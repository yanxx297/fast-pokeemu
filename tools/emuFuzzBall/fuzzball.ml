(*
  Copyright (C) BitBlaze, 2009-2010, and copyright (C) 2010 Ensighta
  Security Inc.  All rights reserved.
*)


module FM = Fragment_machine

module SRFM = Sym_region_frag_machine.SymRegionFragMachineFunctor
  (Symbolic_domain.SymbolicDomain)

module SPFM = Sym_path_frag_machine.SymPathFragMachineFunctor
  (Symbolic_domain.SymbolicDomain)

module IM = Exec_influence.InfluenceManagerFunctor
  (Symbolic_domain.SymbolicDomain)

let fm_ref = ref None
let dt_ref = ref None
let form_man_ref = ref None
let gamma_ref = ref None
let iteration = ref 0
let timestamp = ref (Unix.gettimeofday ())
let outdir = ref "fuzzball-output"
let debug = ref false
let hierarchical_output_dirs = ref false
let concretize_exps = ref []
let simulated_exits = ref []
let invars_exprs = Hashtbl.create 79
let paths_limit = ref 256

let strip str =
    Str.global_replace (Str.regexp_string "\n") "" str


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


(* ===--------------------------------------------------------------------=== *)
let print_ce chan ce =
  Query_engine.ce_iter ce (fun var value -> Printf.fprintf chan "%s=0x%Lx\n" var value)

let var_to_string v = 
  strip(Vine.var_to_string v)

let exp_to_string e = 
  strip(Vine.exp_to_string e)

let in_to_out str = 
  Str.global_replace (Str.regexp_string "in_") "out_" str


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
    

(* ===--------------------------------------------------------------------=== *)
let finish_path_hook fm dt form_man gamma = 
  Printf.printf "*******************************************************************************\n";
  let eip = fm#get_word_var Fragment_machine.R_EIP in
  if List.mem eip !Exec_options.opt_ignored_paths then (
    Printf.printf "PATH COMPLETED (iteration:%d, eip:%.8Lx, time:%.3fs)\n" !iteration eip ((Unix.gettimeofday ()) -. !timestamp);
    Printf.printf "This path will be ignored!!\n";
    Printf.printf "Path: %s\n" dt#get_hist_str_bracketed;    
  ) else (
    let curoutdir = 
      if not !hierarchical_output_dirs then
	Printf.sprintf "%.8d" !iteration	
      else
	Printf.sprintf "%.4d/%.8d" (!iteration mod 4096) 
	  !iteration 
    in
    let curoutdir = mkdir !outdir curoutdir in

    Printf.printf "PATH COMPLETED (iteration:%d, eip:%.8Lx, time:%.3fs outdir:%s)\n" 
      !iteration eip ((Unix.gettimeofday ()) -. !timestamp) curoutdir;

    let (decls, temps1, pathcond, _, _) = 
      form_man#collect_for_solving [] fm#get_path_cond Vine.exp_true in
    let invars = form_man#get_input_vars in
    let decls = list_unique (decls @ invars) in
    let outvars = ref [] in
    let temps2 = ref [] in

    List.iter (fun v -> 
      let (_, s, _) = v in
      let e = Hashtbl.find invars_exprs s in
      let e' = fm#eval_expr_to_symbolic_expr e in 
      let (nt, t) = form_man#walk_temps (fun tv te -> (tv, te)) e' in
      temps2 := t @ !temps2;
      outvars := (v, e) :: !outvars
    ) invars;
    
    temps2 := list_unique(temps1 @ (List.rev !temps2));

    if !debug then
      Printf.printf "Path condition: %s\n" (exp_to_string pathcond);
  
    let feasible, ce = fm#query_with_path_cond Vine.exp_true false in
    (* Printf.printf "\nInput satisfying the path condition:\n";
    print_ce stdout ce; *)
    let fname = Printf.sprintf "%s/testcase" curoutdir in
    let chan = open_out fname in
    print_ce chan ce;
    close_out chan;

    Printf.printf "Path: %s\n" dt#get_hist_str_bracketed;
    let fname = Printf.sprintf "%s/path" curoutdir in
    let chan = open_out fname in
    output_string chan dt#get_hist_str;
    close_out chan;

    let fname = Printf.sprintf "%s/prog" curoutdir in
    let chan = open_out fname in
    List.iter (fun v -> Printf.fprintf chan "var %s;\n" (var_to_string v)) 
      (decls);
    List.iter (fun v -> Printf.fprintf chan "var %s;\n" 
      (in_to_out (var_to_string v))) (invars);
    List.iter (fun (v, e) -> 
      Printf.fprintf chan "var %s;\n" (var_to_string v)) (!temps2); 
    Printf.fprintf chan "var pathcond_%d_%d:reg1_t;\n\n" !iteration 
      (65535 - !iteration);
    Printf.fprintf chan "\n";
    List.iter (fun (v, e) -> 
      Printf.fprintf chan "%s = %s;\n" (var_to_string v) 
	(strip(exp_to_string e))) (!temps2); 
    Printf.fprintf chan "\n";
    List.iter (fun (v, e) -> 
      Printf.fprintf chan "%s = %s;\n" (in_to_out (var_to_string v)) 
	(strip (fm#eval_expr_to_string e))) (!outvars);
    Printf.fprintf chan "\npathcond_%d_%d:reg1_t = %s;\n" !iteration 
      (65535 - !iteration) (strip(exp_to_string pathcond));
    close_out chan;
    
    let fname = Printf.sprintf "%s/time" curoutdir in
    let chan = open_out fname in
    Printf.fprintf chan "%f\n" ((Unix.gettimeofday ()) -. !timestamp);
    close_out chan;

    iteration := !iteration + 1
  );

  timestamp := Unix.gettimeofday ();
  Printf.printf "*******************************************************************************\n\n";

  if !iteration > !paths_limit then 
    raise Exec_exceptions.TooManyIterations

(* ===--------------------------------------------------------------------=== *)
let finish_path_hook_wrapper () =
  match (!fm_ref, !dt_ref, !form_man_ref, !gamma_ref) with
    | (Some fm, Some dt, Some form_man, Some gamma) -> 
      finish_path_hook fm dt form_man gamma
    | _ -> ()


let eip_hook fm dt gamma eip =
  List.iter (fun (eip', exp, va) ->
    if eip' = eip then (
      let va = fm#eval_expr_to_int64 va in
      let _ = match exp with 
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
      Printf.printf "At %08Lx, hardcoding %s to 0x%Lx\n" eip 
	(Vine.exp_to_string exp) va
    )
  ) !concretize_exps;

  List.iter (fun (eip') -> 
    if eip' = eip then (
      Printf.printf "At %08Lx, simulating exit\n" eip;
      raise (Exec_exceptions.SimulatedExit(0L))
    ) 
  ) !simulated_exits


let eip_hook_wrapper (eip) =
  match (!fm_ref, !dt_ref, !form_man_ref, !gamma_ref) with
    | (Some fm, Some dt, Some form_man, Some gamma) -> 
      eip_hook fm dt gamma eip
    | _ -> ()  

(* ===--------------------------------------------------------------------=== *)
let main argv = 
  let concretize_exps_str = ref [] in
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
		  ("-paths-limit", Arg.String
		    (fun s -> paths_limit := (int_of_string s)),
		   " Stop if too many paths are executed");
		  ("-output-dir", Arg.String
		    (fun s -> outdir := s),
		   "dir Store output in dir");
		  ("-simulate-exit", Arg.String
		    (fun s -> simulated_exits := (Int64.of_string s) :: !simulated_exits),
		   "addr Simulate an exit at addr");
		  ("-hierarchical-output-dirs", 
		   Arg.Set(hierarchical_output_dirs),
		   " Create a hierarchical output dirs structure ");
		  ("-concretize-expr", Arg.String
		    (fun s -> 
		      let (eip, exp, va) =  
			let (eip, expva) = Exec_options.split_string '#' s in 
			let (exp, va) = Exec_options.split_string '#' expva in
			(eip, exp, va) in
		      concretize_exps_str := (Int64.of_string(eip), exp, va) ::
		    !concretize_exps_str),
		   "eip#expr#expr bla bla bla");
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
       ((srfm :> FM.fragment_machine),
	(im :> Exec_no_influence.influence_manager), spfm#get_form_man))
  in
  let dl = Asmir.decls_for_arch Asmir.arch_i386 in
  let asmir_gamma = Asmir.gamma_create 
    (List.find (fun (i, s, t) -> s = "mem") dl) dl
  in
    (* create a list of vine expressions representing the memory locations
       which we initially make symbolic *)
  List.iter(fun (a, n) -> 
    let a = Vine.Constant(Vine.Int(Vine.REG_32, a)) in
    let m = Asmir.gamma_lookup asmir_gamma "$mem" in
    let e = Vine.Lval(Vine.Mem(m, a, Vine.REG_8)) in
    Hashtbl.add invars_exprs n e;
  ) !Exec_set_options.opt_symbolic_bytes;
  fm#init_prog (dl, []);
  fm#set_finish_path_hook finish_path_hook_wrapper;
  fm#set_eip_hook eip_hook_wrapper;
  Exec_set_options.default_on_missing := (fun fm -> fm#on_missing_symbol);
  Exec_set_options.apply_cmdline_opts_early fm dl;
  Options_linux.apply_linux_cmdline_opts fm;
  Options_solver.apply_solver_cmdline_opts fm;
  State_loader.apply_state_loader_cmdline_opts fm;
  Exec_set_options.apply_cmdline_opts_late fm;
  fm_ref := Some fm;
  dt_ref := Some dt;
  form_man_ref := Some form_man;
  gamma_ref := Some asmir_gamma;
  let symbolic_init = Exec_set_options.make_symbolic_init fm infl_man in
  List.iter (fun (eip, exp, va) -> 
    let exp = (Vine_parser.parse_exp_from_string dl exp) in
    let va =  (Vine_parser.parse_exp_from_string dl va) in
    assert ((Vine_typecheck.infer_type_fast exp) = 
	(Vine_typecheck.infer_type_fast va));
    concretize_exps := (eip, exp, va) :: !concretize_exps) 
    !concretize_exps_str;
  let (start_addr, fuzz_start) = Exec_set_options.decide_start_addrs () in
  Exec_fuzzloop.fuzz start_addr fuzz_start
    !Exec_options.opt_fuzz_end_addrs fm asmir_gamma symbolic_init
    (fun _ -> ())
;;

main Sys.argv;;
