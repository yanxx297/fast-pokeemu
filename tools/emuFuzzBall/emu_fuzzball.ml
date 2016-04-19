(*
  Copyright (C) BitBlaze, 2009-2010, and copyright (C) 2010 Ensighta
  Security Inc.  All rights reserved.
*)
open Query_engine;;
open Formula_manager;;

module FM = Fragment_machine

module SRFM = Sym_region_frag_machine.SymRegionFragMachineFunctor
  (Symbolic_domain.SymbolicDomain)

module SPFM = Sym_path_frag_machine.SymPathFragMachineFunctor
  (Symbolic_domain.SymbolicDomain)

module IM = Exec_influence.InfluenceManagerFunctor
  (Symbolic_domain.SymbolicDomain)

let fm_ref = ref None
let dt_ref = ref None
let dl_ref = ref None
let form_man_ref = ref None
let gamma_ref = ref None
let iteration = ref 0
let fuzz_start_eip = ref 0L
let ignore_contions_till_eip = ref 0L
let timestamp = ref (Unix.gettimeofday ())
let outdir = ref "fuzzball-output"
let debug = ref false
let hierarchical_output_dirs = ref false
let exit_status_exps = ref []

let concretize_exps = ref []
let simulated_exits = ref []
let paths_limit = ref 256
let running_symbolically = ref false
let tracing_start_eip = ref 0L
let tracing_enabled = ref false
let trace = ref []

let symbolic_bytes = Hashtbl.create 131
let opt_symbolic_bytes_lazy = ref []
let symbolic_bytes_lazy = Hashtbl.create 39
let tracked_regions = ref []
let stores = Hashtbl.create 79

let ignored_conditions = ref 0
let preferred_values = Hashtbl.create 79

let randseed = Random.int 0xfffffff

let starts_with str pat = 
  let n = min (String.length pat) (String.length str) in
  (String.sub str 0 n) = pat


let strip str =
  Str.global_replace (Str.regexp_string "\n") "" str


let fillrow pat =
  let cols = 
    try int_of_string (Sys.getenv "COLUMNS")
    with Not_found -> 80
  in
  for i = 0 to cols - 1 do
    Printf.printf "%c" pat
  done;
  Printf.printf "\n"


let list_unique l =
  let h = Hashtbl.create 10 in
  let rec loop = function
    | [] -> []
    | e :: el ->
        if Hashtbl.mem h e then
          loop el
        else
          (Hashtbl.replace h e ();
           e :: (loop el))
  in
    (loop l)


(* Extract a slice from a list. *)
let list_slice l b e =
  let rec slice l b e f =
    match l with
      | [] -> f
      | h::t -> 
	if (b < 2) then (
          if (e > 0) then ( 
	    slice t b (e-1) (f@[h]) 
	  ) else (
	    f
	  )
	) else ( 
	  slice t (b-1) (e-1) f 
	)
  in
  slice l b e []


let split str sep = 
  Str.split (Str.regexp_string sep) str


let replace str f t =
  Str.global_replace (Str.regexp_string f) t str


(* Build a hash table from a list of pairs *)
let hash l = 
  let h = Hashtbl.create (List.length l) in
  List.iter(fun (a, b) -> assert (not (Hashtbl.mem h a)); Hashtbl.add h a b) l;
  h


(* Return a list of keys of a hash table *)
let keys map =
  Hashtbl.fold (fun k v acc -> k :: acc) map []


(* Return a list of values of a hash table *)
let values map =
  Hashtbl.fold (fun k v acc -> v :: acc) map []


(* Return a list of key/value pairs of a hash table *)
let items map =
  Hashtbl.fold (fun k v acc -> (k, v) :: acc) map []


let var_to_string v = 
  replace (strip (Vine.var_to_string v)) "  " " "


let exp_to_string e = 
  replace (strip (Vine.exp_to_string e)) "  " " "


let size_for_ty ty = 
  match ty with 
    | Vine.REG_8 -> 8
    | Vine.REG_16 -> 16
    | Vine.REG_32 -> 32
    | Vine.REG_64 -> 64
    | _ -> failwith "Unsupported type"  


let mkdir base dirs = 
  let mkdir dir = 
    try
      Unix.mkdir dir 0o700;
      dir
    with
      | Unix.Unix_error(Unix.EEXIST, _, _) -> dir
  in
  let dirs = Str.split (Str.regexp_string "/") dirs in
  List.fold_left (fun base dir -> mkdir (base ^ "/" ^ dir)) base dirs

    
let gzip_open_out f = 
  Gzip.open_out f


let gzip_close_out f = 
  Gzip.close_out f


let gzip_output chan buf =
  String.iter(fun c -> Gzip.output_char chan c) buf

(* ===--------------------------------------------------------------------=== *)

(* Build a memory expression for a given address *)
let mem_exp a =
  let a = Vine.Constant(Vine.Int(Vine.REG_32, a)) in
  let gamma = match !gamma_ref with
    | Some gamma -> gamma
    | None -> failwith "missing gamma"
  in
  let m = Asmir.gamma_lookup gamma "$mem" in
  Vine.Lval(Vine.Mem(m, a, Vine.REG_8))


(* Return a slice of the path condition *)
let prune_pathcond pc =
  let ignored = !ignored_conditions in
  let pcs = List.length pc in
  let pc_no_extra = list_slice pc 0 (pcs - ignored)  in
  pc_no_extra


(* Return a list of variables in the path condition  *)
let vars_in_pathcond pc = 
  let form_man = Option.get !form_man_ref in
  let (decls, temps, _, _, _) =  form_man#collect_for_solving [] pc 
    Vine.exp_true in
  (* remove input vars that are temporaries introduces by lets *)
  (List.filter(fun (i,n,t) ->  not (starts_with n "t")) decls),
  temps


(* Test satisfiablility of the path condition in a given context *)
let test_satisfiability decls temps pc ctx =
  let form_man = Option.get !form_man_ref in
  let ctx' = ref (List.filter (fun (n,v) -> 
    ((starts_with n "in_") || (starts_with n "mem_byte_"))
  ) (items ctx)) in
  (* Add missing variables from the PC to the CTX (initialized with random
     value *)
  List.iter(fun (_,n,_) -> 
    if not (Hashtbl.mem ctx n) then
      ctx' := (n, 0x0L) :: !ctx') decls;

  (* Initialize the context (i.e., assign to each input var a concrete value) *)
  Interpreter.ctx_init !ctx';
  (* Evaluate temporaries *)
  Interpreter.eval_assgns temps;
  (* Evaluate the path condition in the current context *)
  let conds = Formula_manager.conjoin pc in
	(*Printf.printf "Cond: %s\n" (Vine.exp_to_string conds);*)
  Interpreter.eval_exp conds = 1L
  

(* Refine the value for a given variable by minimizing the distance from a
   preferred (concrete) value *)
let compute_preferred_value decls temps pc ctx var curval prefval verbose =
  let set_ctx v = Hashtbl.replace ctx var v in
  let get_ctx () = Hashtbl.find ctx var in
  let xor64 a b = Int64.logxor a b in
  let and64 a b = Int64.logand a b in
  let diff = xor64 curval prefval in

  (* sanity check *)
  assert (test_satisfiability decls temps pc ctx);

  for i = 0 to 7 do
    let m = Int64.of_int (1 lsl i) in 
    (* Process only differing bits *)
    if (and64 m diff) <> 0L then (
      (* Flip the bit (as in the preferred value) *)
      set_ctx (xor64 (get_ctx ()) m);

      (* Check whether the path is feasible if the bit is flipped *)
      if not (test_satisfiability decls temps pc ctx) then (
	(* the bit is relevant, re-flip it (as in the current value) *)
	set_ctx (xor64 (get_ctx ()) m);
	if verbose then
	  Printf.printf "Bit %d of %s is relevant (unsat)\n" i var;
      ) else (
	(* the bit is irrelevant, keep it flipped (as in the preferred
	   value) *)
	if verbose then
	  Printf.printf "Bit %d of %s is irrelevant (sat)\n" i var;
      )
    );
  done;

  Printf.printf "Relevance analysis (%s): 0x%.2Lx vs. 0x%.2Lx --> 0x%.2Lx\n" 
    var curval prefval (get_ctx ());

  get_ctx ()


(* Build the test-case (skip variables used only in extra conditions and try to
   return ideal assignments) *)
let assemble_testcase pc ctx =
  let (decls, temps) = vars_in_pathcond pc in
  let decls' = List.map(fun (_, n, _) -> n) decls in
  let tcs = 
    Hashtbl.fold (fun var curval acc -> 
      if List.mem var decls' then (
	let tc = 
	  if Hashtbl.mem preferred_values var then (
	    let prefval = Hashtbl.find preferred_values var in
	    let ctx' = Hashtbl.copy ctx in 
	    (var, (compute_preferred_value decls temps pc ctx' var curval 
		     prefval true))
	  ) else (
	    (var, curval)
	  )
	in
	tc :: acc
      ) else (
	acc
      )
    ) ctx []
  in
  tcs


let evaluate pc ctx exp =
  let (decls, temps) = vars_in_pathcond pc in
  let ctx' = ref (List.filter (fun (n,v) -> starts_with n "in_") (items ctx)) in
  (* Add missing variables from the PC to the CTX *)
  List.iter(fun (_,n,_) -> if not (Hashtbl.mem ctx n) then
      ctx' := (n, Random.int64 0xffL) :: !ctx') decls;

  List.iter(fun (v, e) -> Printf.printf "TMP: %s  -->  %s\n" (var_to_string v) (exp_to_string e)) temps;
  Printf.printf "\n\n";
  List.iter(fun (v,n) -> Printf.printf "CTX: %s %Lx\n" v n) !ctx';

  (* Initialize the context (i.e., assign to each input var a concrete value) *)
  Interpreter.ctx_init !ctx';
  (* Evaluate temporaries *)
  Interpreter.eval_assgns temps;
  Printf.printf "TEMPS evaluated\n";
  (* Evaluate expression *)
  let r = Interpreter.eval_exp exp in
  Printf.printf "Expression %s ---> %Lx\n" (exp_to_string exp) r;
  r


let concretize exp = 
  let fm = Option.get !fm_ref in
  let form_man = Option.get !form_man_ref in
  let dt = Option.get !dt_ref in

  Printf.printf "Concretize %s in %s\n" (exp_to_string exp) (dt#get_hist_str);

  let feasible, ce = fm#query_with_path_cond Vine.exp_true false in
  assert (feasible);
    form_man#eval_expr_from_ce ce exp


(* ===--------------------------------------------------------------------=== *)

let finish_path_hook fm dt form_man gamma = 
  let sprintf = Printf.sprintf in
  let fprintf = Printf.fprintf in
  let printf = Printf.printf in

  let eip = fm#get_word_var Fragment_machine.R_EIP in
  if List.mem eip !Exec_options.opt_ignored_paths then (
    printf "PATH COMPLETED (iteration:%d, eip:%.8Lx, time:%.3fs)\n" !iteration eip ((Unix.gettimeofday ()) -. !timestamp);
    printf "This path will be ignored!!\n";
    printf "Path: %s\n" dt#get_hist_str_bracketed;    
  ) else (
    let curoutdir = 
      if not !hierarchical_output_dirs then
	sprintf "%.8d" !iteration	
      else
	sprintf "%.4d/%.8d" (!iteration mod 4096) 
	  !iteration 
    in
    let curoutdir = mkdir !outdir curoutdir in

    printf "PATH COMPLETED (iteration:%d, eip:%.8Lx, instructions:%d time:%.3fs outdir:%s)\n" 
      !iteration eip (List.length !trace) ((Unix.gettimeofday ()) -. !timestamp) curoutdir;

    let fname = sprintf "%s/exitstatus" curoutdir in
    let chan = open_out fname in
    List.iter (fun (n,e) -> 
			(try 
				Printf.fprintf chan "%s=0x%Lx\n" 
      n (fm#eval_expr_to_int64 e) 
			with Exec_exceptions.NotConcrete(e) -> (
				let (_, ce) = fm#query_with_path_cond Vine.exp_true false in
				Printf.fprintf chan "%s=0x%Lx\n"  
			n (evaluate fm#get_path_cond (hash (Query_engine.ce_filter ce (fun n v -> not (starts_with n "t")))) e)));) !exit_status_exps;
    close_out chan;

    let (decls, pathcond_temps, pathcond, _, _) = 
      form_man#collect_for_solving [] fm#get_path_cond
	Vine.exp_true in
    (* Eval the current content of written memory locations *)
    let outvars = List.map (fun (v,a) -> 
      (v, (fm#eval_expr_to_symbolic_expr (mem_exp a)))) (items stores) in
    (* Get variables and temporaries that appear in outvars *)
    let (nontemps, temps) = 
      List.fold_left (fun (accnt, acct) (n, e) -> 
	let (nt, t) = form_man#walk_temps (fun tv te -> (tv, te)) e in
	(nt @ accnt, t @ acct))
	(decls, pathcond_temps) outvars
    in
    let (nontemps, temps) = ((list_unique nontemps), (list_unique temps)) in


    printf "Path: %s\n" dt#get_hist_str_bracketed;
    let fname = sprintf "%s/path" curoutdir in
    let chan = gzip_open_out fname in
    gzip_output chan dt#get_hist_str_bracketed;
    gzip_close_out chan;

    let fname = sprintf "%s/program" curoutdir in
    let chan = gzip_open_out fname in
    List.iter (fun (v) -> 
      gzip_output chan (sprintf "var %s; // Invar\n" (var_to_string v))) 
      (nontemps);
    List.iter (fun (v, e) -> 
      gzip_output chan (sprintf "var %s; // Temp \n" (var_to_string v))) 
      (temps);
    List.iter (fun (n, e) -> 
      gzip_output chan (sprintf "var %s:reg8_t;\n" n))
      (outvars);
    gzip_output chan (sprintf "var pathcond_%d_%d:reg1_t;\n\n" !iteration
      (65535 - !iteration));
    List.iter (fun (v, e) -> 
      gzip_output chan (sprintf "%s = %s;\n" (var_to_string v)
	(exp_to_string e))) temps; 
    gzip_output chan "\n";
    List.iter (fun (v, e) -> 
      gzip_output chan (sprintf "%s:reg8_t = %s;\n" v 
      (exp_to_string e))) (outvars);
    gzip_output chan (sprintf "\npathcond_%d_%d:reg1_t = %s;\n" !iteration 
			(65535 - !iteration) (exp_to_string pathcond));
    gzip_close_out chan;

    let feasible, ce = fm#query_with_path_cond Vine.exp_true false in
    assert (feasible);
    let testcase = assemble_testcase (prune_pathcond fm#get_path_cond) 
      (*(hash (List.filter (fun (n,v) -> not (starts_with n "t")) ce)) in*)
			(hash (Query_engine.ce_filter ce (fun n v -> not (starts_with n "t")))) in
    let fname = sprintf "%s/testcase" curoutdir in
    let chan = gzip_open_out fname in
    List.iter(fun (n, v) -> gzip_output chan (sprintf "%s=0x%Lx\n" n v)) 
      testcase;
    gzip_close_out chan;

    let fname = sprintf "%s/time" curoutdir in
    let chan = open_out fname in
    fprintf chan "%f\n" ((Unix.gettimeofday ()) -. !timestamp);
    close_out chan;

    let fname = sprintf "%s/trace" curoutdir in
    let chan = gzip_open_out fname in
    List.iter (fun (eip) -> gzip_output chan (sprintf "%08Lx\n" eip)) 
      (List.rev !trace);
    gzip_close_out chan;

    iteration := !iteration + 1
  );

  ignored_conditions := 0;
  trace := [];
  tracing_enabled := false;
  running_symbolically := false;
  timestamp := Unix.gettimeofday ();
  Hashtbl.clear stores;
  Hashtbl.clear symbolic_bytes_lazy;
  fillrow '*';
  printf "\n";

  if !iteration >= !paths_limit then 
    raise Exec_exceptions.TooManyIterations


(* ===--------------------------------------------------------------------=== *)


let finish_path_hook_wrapper () =
  let fm = Option.get !fm_ref in 
  let dt = Option.get !dt_ref in
  let gamma = Option.get !gamma_ref in
  let form_man = Option.get !form_man_ref in
  finish_path_hook fm dt form_man gamma


let eip_hook fm dt gamma eip =
  let dl = Option.get !dl_ref in

  if eip = !fuzz_start_eip then (
    running_symbolically := true;
    fillrow '*';
    let form_man = Option.get !form_man_ref in
    Printf.printf "At %08Lx, starting symbolic execution (%d input vars)\n" 
      eip (List.length form_man#get_input_vars);
  );

  if eip = !tracing_start_eip then (
    tracing_enabled := true;
    Printf.printf "At %08Lx, enabling tracing\n" eip;
  );

  (* Trace execution *)
  if !tracing_enabled then
    trace := eip :: !trace;

  (* Ignore path conditions before this point (we recordlength of the list) *)
  if eip = !ignore_contions_till_eip then (
    ignored_conditions := (List.length fm#get_path_cond);
    Printf.printf "At %08Lx, ignoring the first %d path conditions\n" eip 
      !ignored_conditions;
  );

  List.iter (fun (eip', exp, va) ->
    if eip' = eip then (
      let newval = 
	match va with
	  | Some va -> Some (fm#eval_expr_to_int64 va) 
	  | None -> None
      in
      let curval = fm#eval_expr_to_symbolic_expr exp in

      match curval with 
	| Vine.Constant(Vine.Int(_, curval)) -> (
	  let store_conc addrexp va = 
	    match addrexp with 
	      | Vine.Lval(Vine.Mem(_, addr, Vine.REG_8)) -> 
		let addr = fm#eval_expr_to_int64 addr in
		fm#store_byte_conc addr (Int64.to_int va)
	      | Vine.Lval(Vine.Mem(_, addr, Vine.REG_16)) ->
		let addr = fm#eval_expr_to_int64 addr in
		fm#store_short_conc addr (Int64.to_int va)
	      | Vine.Lval(Vine.Mem(_, addr, Vine.REG_32)) ->
		let addr = fm#eval_expr_to_int64 addr in
		fm#store_word_conc addr va
	      | Vine.Lval(Vine.Temp(_, name, Vine.REG_32)) -> 
		fm#set_word_var (Fragment_machine.regstr_to_reg name) va
	      | _ -> failwith "unsupported expression"
	  in
	  match newval with 
	    | Some newval -> 
	      (* concrete value, just store the new concrete value in memory *)
	      Printf.printf "At 0x%08Lx, %s is already concrete, hardcoding to 0x%Lx\n" 
		eip (exp_to_string exp) newval;
	      store_conc exp newval;
	    | None ->
	      Printf.printf "At 0x%08Lx, %s is already concrete (%.Lx)\n" eip 
		(exp_to_string exp) curval ;
	)
	| _ -> ( (* symbolic value, concretize by adding an extra condition *)
	  let ty = Vine_typecheck.infer_type_fast curval in
	  (* deterministic PRNG (seeded with path and address) *)
	  let randint addr =
	    let fnvhash h x =
	      let h' = Int32.logxor h (Int32.of_int x) in
	      Int32.mul h' (Int32.of_int 0x1000193) in
	    let path = Int32.to_int (List.fold_left (
	      fun h b -> (fnvhash h (if b then 49 else 48)))
				       (Int32.of_int randseed) (dt#get_hist)) in
	    Printf.printf "Init rand: %x %Lx (path:%s)\n" path addr (dt#get_hist_str);
	    let state = Random.State.make [|path; (Int64.to_int addr)|] in
	    Random.State.int64 state 0xfffL
	  in (
	    match exp with
	      | Vine.Lval(Vine.Mem(_, addr, Vine.REG_32)) ->
		let addr = fm#eval_expr_to_int64 addr in
		let newval = ( 
		  match newval with
		    | Some newval -> newval
		    | None -> randint addr
		    (* | None -> concretize curval *)
		) in
		let cond = Vine.exp_eq curval (Vine.const_of_int64 ty newval) in

		let feasible, _ = fm#query_with_path_cond cond false in
		let (newval', cond') =
                  if feasible then (newval, cond) else
		    (* The randomly chosen value is infeasible. Try to
		       concretize based on the path condition. *)
                    let nv' = concretize curval in
                    let cond' = Vine.exp_eq curval (Vine.const_of_int64 ty nv')
                    in
                    let feasible, _ = fm#query_with_path_cond cond' false in
                      assert(feasible);
                      (nv', cond')
		in
		fm#add_to_path_cond cond';
		Printf.printf "At 0x%08Lx, concretizing %s [0x%08Lx] to 0x%Lx (using extracond. %s)\n" 
		  eip (exp_to_string exp) addr newval' (exp_to_string cond')
	      | _ -> failwith "unsupported expression"
	  )
	)
    )
  ) !concretize_exps;

  (* Simulate an exit when execution reaches a certain target *)
  List.iter (fun (eip') -> 
    if eip' = eip then (
      Printf.printf "At 0x%08Lx, simulating exit\n" eip;
      raise (Exec_exceptions.SimulatedExit(0L))
    ) 
  ) !simulated_exits


let eip_hook_wrapper eip =
  let fm = Option.get !fm_ref in 
  let dt = Option.get !dt_ref in
  let gamma = Option.get !gamma_ref in
  eip_hook fm dt gamma eip


(* ===--------------------------------------------------------------------=== *)

let store_hook fm dt gamma eip addr ty exp = 

  (* Track stores to certain addresses *)
  let matched = ref None in
  List.iter (fun (f, l, n) -> 
    if (addr >= f && addr <= l) then (
      matched := Some (f, l, n);
    )
  ) !tracked_regions;

  match !matched with
    | Some (first, last, name) ->
      Printf.printf "At %08Lx, store %.8Lx (%s) = %s\n" eip addr name exp;
      let store addr i =
	for j = 0 to i / 8 - 1 do
	  let addr = (Int64.add addr (Int64.of_int j)) in
	  let size = (Int64.to_int (Int64.sub last first)) + 1 in
	  let name = 
	    if starts_with name "out_mem_" then 
	      Printf.sprintf "out_mem_%.8Lx___1_0_%u" (Int64.sub addr first) 
		(65535 - !iteration)
	    else if starts_with name "out_fpu_" then 
	      Printf.sprintf "out_fpu_%.8Lx___1_0_%u" (Int64.sub addr first) 
		(65535 - !iteration)
	    else if starts_with name "out_desc_cache" then 
	      Printf.sprintf "out_desc_cache_%Lu_%u" (Int64.sub addr first) 
		(65535 - !iteration)
	    else
	      Printf.sprintf "%s_%d_%u" name j (65535 - !iteration)
	  in
	  Hashtbl.replace stores name addr;
	  if not (Hashtbl.mem symbolic_bytes_lazy addr) then
	    Hashtbl.replace symbolic_bytes_lazy addr "???????"
	done
      in
      store addr ty
    | _ -> ()


let store_hook_wrapper addr ty exp = 
  let fm = Option.get !fm_ref in 
  let dt = Option.get !dt_ref in
  let gamma = Option.get !gamma_ref in
  let eip = fm#get_word_var Fragment_machine.R_EIP in
  if !running_symbolically = true then
    store_hook fm dt gamma eip addr ty exp

(* ===--------------------------------------------------------------------=== *)

let load_hook fm dt gamma eip addr ty = 
  let form_man = Option.get !form_man_ref in

  (* Intercept loads from certain locations and return a fresh symbolic
     variable at the first read access (if not previously written) *)
  let matched = ref None in
  List.iter (fun (f, l, n) -> 
    if (addr >= f && addr <= l) then (
      matched := Some (f, l, n);
    )
  ) !opt_symbolic_bytes_lazy;

  match !matched with
    | Some (first, last, name) ->
      for i = 0 to (ty / 8 - 1) do
	let a = Int64.add addr (Int64.of_int i) in
	assert (not (Hashtbl.mem symbolic_bytes a));
	if (not (Hashtbl.mem symbolic_bytes_lazy a)) then (
	  let name =
	    if starts_with name "in_mem_" then 
	      Printf.sprintf "in_mem_%.8Lx__1_0" (Int64.sub a first)
	    else
	      Printf.sprintf "%s_%d" name i
	  in
	  Printf.printf "At 0x%08Lx, symbolicizing address 0x%08Lx as %s\n" eip
	    a name;
	  fm#store_byte a (form_man#fresh_symbolic_8 name);
	  Hashtbl.add symbolic_bytes_lazy a name;
	) else (
	  Printf.printf "At 0x%08Lx, accessing already symbolicized address 0x%08Lx\n" 
	    eip a; 
	)
      done;
    | _ -> ()


let store_load_wrapper addr ty = 
  let fm = Option.get !fm_ref in 
  let dt = Option.get !dt_ref in
  let gamma = Option.get !gamma_ref in
  let eip = fm#get_word_var Fragment_machine.R_EIP in
  if !running_symbolically = true then
    load_hook fm dt gamma eip addr ty

(* ===--------------------------------------------------------------------=== *)
let main argv = 
  let concretize_exps_str = ref [] in
  let exit_status_exps_str = ref [] in
  Arg.parse
    (Arg.align (Exec_set_options.cmdline_opts
		@ Options_linux.linux_cmdline_opts
		@ State_loader.state_loader_cmdline_opts
		@ Exec_set_options.concrete_state_cmdline_opts
		@ Exec_set_options.symbolic_state_cmdline_opts	
		@ Exec_set_options.concolic_state_cmdline_opts	
		@ Exec_set_options.explore_cmdline_opts
		@ Exec_set_options.fuzzball_cmdline_opts
		@ Options_solver.solver_cmdline_opts
		@ Exec_set_options.trace_replay_cmdline_opts
		@ Exec_set_options.influence_cmdline_opts
		@ [
		  ("-debug", Arg.Set(debug),
		   " Enable debugging output");
		  ("-output-dir", Arg.String
		    (fun s -> outdir := s),
		   "dir Store output in dir");
		  ("-exit-status-exp", Arg.String
		    (fun s -> 
		      let (n,e) = Exec_options.split_string '#' s in
		      exit_status_exps_str := (n,e) :: !exit_status_exps_str),
		   "name=exp Evaluate expression of the end of the path");
		  ("-paths-limit", Arg.String
		    (fun s -> paths_limit := (int_of_string s)),
		   " Stop if too many paths are executed");
		  ("-output-dir", Arg.String
		    (fun s -> outdir := s),
		   "dir Store output in dir");
		  ("-simulate-exit", Arg.String
		    (fun s -> simulated_exits := 
		      (Int64.of_string s) :: !simulated_exits),
		   "addr Simulate an exit at addr");
		  ("-ignore-pc-till", Arg.String
		    (fun s -> ignore_contions_till_eip := (Int64.of_string s)),
		   "addr Simulate an exit at addr");
		  ("-trace-from", Arg.String
		    (fun s -> tracing_start_eip := (Int64.of_string s)),
		   "addr Simulate an exit at addr");
		  ("-dump-region", Arg.String
		    (fun s -> 
		      let (first, s) = Exec_options.split_string ':' s in 
		      let first = Int64.of_string first in 
		      let (size, name) = Exec_options.split_string '=' s in
		      let size = Int64.of_string size in 
		      let last = Int64.sub (Int64.add first size) 1L in
		      tracked_regions := (first, last, name) :: !tracked_regions
		    ),
		   "first:last:name Include variable in the final output if modified");
		  ("-hierarchical-output-dirs", 
		   Arg.Set(hierarchical_output_dirs),
		   " Create a hierarchical output dirs structure ");
		  ("-preferred-value", Arg.String
		    (fun s ->
		      let (vr, vl) = Exec_options.split_string ':' s in
		      Hashtbl.add preferred_values vr (Int64.of_string vl)),
		   "var:val Preferred value for variable");
		  ("-concretize-expr", Arg.String
		    (fun s -> 
		      let (eip, exp, va) =  
			let (eip, expva) = Exec_options.split_string '#' s in 
			let (exp, va) = Exec_options.split_string '#' expva in
			(eip, exp, va) in
		      concretize_exps_str := (Int64.of_string(eip), exp, va) ::
			!concretize_exps_str),
		   "eip#expr1#expr2 Concretize expr1 to expr2 at addr");
		  ("-symbolic-bytes-lazy", Arg.String
		   (fun s ->
		     let (first, s) = Exec_options.split_string ':' s in
		     let first = Int64.of_string first in
		     let (size, name) = Exec_options.split_string '=' s in
		     let size = Int64.of_string size in
		     let last = Int64.sub (Int64.add first size) 1L in
		     opt_symbolic_bytes_lazy := (first, last, name) :: 
		       !opt_symbolic_bytes_lazy),
		   "addr:size=name Make symbolic bytes lazily");
		]))
    (fun arg -> Exec_set_options.set_program_name arg)
    "fuzzball [options]* program\n";

  let dt = ((new Binary_decision_tree.binary_decision_tree)
	    :> Decision_tree.decision_tree)#init in
  let (fm, infl_man, form_man) = 
    (let srfm = new SRFM.sym_region_frag_machine dt in
     let spfm = (srfm :> SPFM.sym_path_frag_machine) in
     let im = new IM.influence_manager spfm in
     srfm#set_influence_manager im;
     fm_ref := Some srfm;
     ((srfm :> FM.fragment_machine),
      (im :> Exec_no_influence.influence_manager), spfm#get_form_man))
  in
  let dl = Asmir.decls_for_arch Asmir.arch_i386 in
  let asmir_gamma = Asmir.gamma_create 
    (List.find (fun (i, s, t) -> s = "mem") dl) dl
  in

  fm#init_prog (dl, []);

  (* Custom hooks *)
  fm#set_finish_path_hook finish_path_hook_wrapper;
  fm#set_eip_hook eip_hook_wrapper;
  fm#set_store_hook store_hook_wrapper;
  fm#set_load_hook store_load_wrapper;

  List.iter(fun (a, n) -> Hashtbl.replace symbolic_bytes a n) 
    !Exec_set_options.opt_symbolic_bytes;

  Exec_set_options.default_on_missing := (fun fm -> fm#on_missing_symbol);
  Exec_set_options.apply_cmdline_opts_early fm dl;
  Options_linux.apply_linux_cmdline_opts fm;
  Hashtbl.add Options_solver.solvers_table "z3vc"
    (fun _ -> Some new Z3vc_query_engine.z3vc_engine);
  Options_solver.apply_solver_cmdline_opts fm;
  State_loader.apply_state_loader_cmdline_opts fm;
  Exec_set_options.apply_cmdline_opts_late fm;

  dl_ref := Some dl;
  dt_ref := Some dt;
  form_man_ref := Some form_man;
  gamma_ref := Some asmir_gamma;

  let symbolic_init = Exec_set_options.make_symbolic_init fm infl_man in

  List.iter (fun (eip, exp, va) -> 
    let exp = (Vine_parser.parse_exp_from_string dl exp) in
    let va = 
      if va <> "" then
	Some (Vine_parser.parse_exp_from_string dl va)
      else
	None
    in
    concretize_exps := (eip, exp, va) :: !concretize_exps
  ) !concretize_exps_str;

  exit_status_exps := List.map (fun (n, e) -> 
    (n, (Vine_parser.parse_exp_from_string dl e))
  ) !exit_status_exps_str;

  let (start_addr, fuzz_start) = Exec_set_options.decide_start_addrs () in
  fuzz_start_eip := fuzz_start;
  running_symbolically := false;
  if !ignore_contions_till_eip = 0L then
    ignore_contions_till_eip := !fuzz_start_eip;

  try
    Exec_fuzzloop.fuzz start_addr fuzz_start
      !Exec_options.opt_fuzz_end_addrs fm asmir_gamma symbolic_init
      (fun _ -> ())
  with Exec_exceptions.TooManyIterations -> Printf.printf "Too many iterations";
    exit 1;
;;

main Sys.argv;;
