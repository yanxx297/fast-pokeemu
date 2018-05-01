(*
  Copyright (C) BitBlaze, 2009-2010, and copyright (C) 2010 Ensighta
  Security Inc.  All rights reserved.
*)

module V = Vine
open Printf
open Unix

let prog1 = ref ""
let prog2 = ref ""
let cpu_decls = Asmir.decls_for_arch Asmir.arch_i386

(* Unlike Vine_util.list_unique, this preserves order (keeping the
   first occurrence) which is important because the temps have to retain
   a topological ordering. *)
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


let starts_with str pat = 
  let n = String.length pat in
  String.sub str 0 n = pat


let strip str =
    Str.global_replace (Str.regexp_string "\n") "" str

let keys map =
  Hashtbl.fold (fun k v acc -> k :: acc) map []

let values map =
  Hashtbl.fold (fun k v acc -> v :: acc) map []

let var_to_string v = strip(V.var_to_string v)
let exp_to_string e = strip(V.exp_to_string e)
let stmt_to_string s = strip(V.stmt_to_string s)


let iter_dir func dirname =
  let d = opendir dirname in
  try 
    while true do 
      let file = readdir d in
      match file with
	| "." -> ()
	| ".." -> ()
	| _ -> let full = dirname ^ "/" ^ file in 
	       func full
    done
  with End_of_file -> closedir d


let cleanup_var i = 
  String.concat "_" (List.rev(List.tl(List.rev(
    Str.split (Str.regexp_string "_") i))))


let rename_var_in_decl map oldvar =
    let (i, n, t) = oldvar in 
    try
      Hashtbl.find map n
    with 
      | Not_found -> oldvar
	

(* Rename all occurrences of a set of variables with new variables *)
let rename_var_in_stmt map oldstmt =
  let rename_var oldvar =
    let (i, n, t) = oldvar in 
    try
      let newvar = Hashtbl.find map n in
      newvar
    with 
      | Not_found -> oldvar
  in
  let rec exp_loop = function
    | V.Name(s) as n -> n
    | V.BinOp(op, e1, e2) -> V.BinOp(op, (exp_loop e1), (exp_loop e2))
    | V.UnOp(op, e1) -> V.UnOp(op, (exp_loop e1))
    | V.Cast(ct, ty, e1) -> V.Cast(ct, ty, (exp_loop e1))
    | V.Lval(lv) -> V.Lval(lv_loop lv)
    | V.Let(lv, e1, e2) ->
        V.Let((lv_loop lv), (exp_loop e1), (exp_loop e2))
    | e -> e
  and lv_loop = function
    | V.Temp(v) -> V.Temp(rename_var v)
    | V.Mem(v, e, ty) -> V.Mem(v, (exp_loop e), ty)
  in
  let rec st_loop = function
    | V.Label(s) as l -> l
    | V.Jmp(e1) -> V.Jmp(exp_loop e1)
    | V.CJmp(e1, e2, e3) -> V.CJmp((exp_loop e1), (exp_loop e2), (exp_loop e3))
    | V.Move(lv, e1) -> V.Move((lv_loop lv), (exp_loop e1))
    | V.ExpStmt(e1) -> V.ExpStmt(exp_loop e1)
    | V.Block(dl, sl) -> V.Block(dl, (List.map st_loop sl))
    | V.Assert(e1) -> V.Assert(exp_loop e1)
    | V.Halt(e1) -> V.Halt(exp_loop e1)
    | st -> st
  in
  st_loop oldstmt

   
let parse_prog dir = 
  printf "Parsing %s\n" dir;
  let prog = Vine_parser.parse_file (dir ^ "/prog") in
  let (decls, stmts) = prog in
  let chan = open_out (dir ^ "/prog.parsed") in
  List.iter (fun decl -> fprintf chan "%s\n" (var_to_string decl)) decls;
  fprintf chan "\n\n";
  List.iter (fun stmt -> fprintf chan "%s\n" (stmt_to_string stmt)) stmts;
  close_out chan;
  prog


let print_prog prog = 
  let (decls, stmts) = prog in 
  List.iter (fun v -> printf "var %s;\n" (var_to_string v)) decls;
  printf "\n";
  List.iter (fun s -> printf "%s\n" (stmt_to_string s)) stmts


let parse_prog_paths prog = 
  let decls = ref [] in
  let stmts = ref [] in
  let in_out_pc = ref [] in
  let parse f = 
    let (decls_, stmts_) = parse_prog f in 
    decls := list_unique (!decls @ decls_);
    stmts := !stmts @ stmts_;
    let filter_inputs (i, n, v) = starts_with n "in_" in
    let filter_outputs (i, n, v) = starts_with n "out_" in
    let filter_pathcond (i, n, v) = starts_with n "pathcond_" in
    let (inputs, outputs, pathcond) = 
      ((List.filter filter_inputs decls_), 
       (List.filter filter_outputs decls_),
       (List.hd(List.filter filter_pathcond decls_))) in
    in_out_pc := !in_out_pc @ [(inputs, outputs, pathcond)];
    ()
  in
  iter_dir parse prog;

  let decls = !decls in
  let stmts = !stmts in
  let in_out_pc = !in_out_pc in
  (decls, stmts, in_out_pc)


let merge_progs prog1 prog2 = 
  let (decls1, stmts1, in_out_pc1) = prog1 in
  let (decls2, stmts2, in_out_pc2) = prog2 in

  (* maps used to unify inputs *)
  let old_to_new_inputs = Hashtbl.create 79 in
  let new_inputs = Hashtbl.create 79 in
  let old_to_new_outputs = Hashtbl.create 79 in
  let new_outputs = Hashtbl.create 79 in

  (* map multiple instances of the same variable to a unique instance *)
  let rebind_var vars nmap omap = 
    List.iter (fun (i, n, t) ->
      let m = cleanup_var n in
      if not (Hashtbl.mem nmap m) then
	Hashtbl.add nmap m (V.newvar m t);
      Hashtbl.add omap n (Hashtbl.find nmap m);
      ()
    ) vars in
  List.iter (fun (i, o, p) -> 
    rebind_var i new_inputs old_to_new_inputs;
    rebind_var o new_outputs old_to_new_outputs)
    (in_out_pc1 @ in_out_pc2);
  
  (* merge statements and declarations and rename all occurrences of old inputs
     with the new ones *)
  let rename_stmt stmt = rename_var_in_stmt old_to_new_inputs stmt in 
  let rename_decl var = rename_var_in_decl old_to_new_inputs var in
  let stmts = List.map rename_stmt (stmts1 @ stmts2) in
  let rename_iop (i, o, pc) = ((List.map rename_decl i), o, (rename_decl pc)) in
  let in_out_pc1 = List.map rename_iop in_out_pc1 in
  let in_out_pc2 = List.map rename_iop in_out_pc2 in

  (* remove old inputs and add the new ones to the list of decls *)
  let filter (i, n, t) = not (Hashtbl.mem old_to_new_inputs n) in
  let decls = (values new_inputs) (* @ (List.filter filter (decls1 @ decls2)) *) in

  print_prog (decls, stmts);

  (* map a given output to its possible values [(pc1 -> out1), (pc2 -> out2)] *)
  let pc_outs1 = Hashtbl.create 79 in
  let pc_outs2 = Hashtbl.create 79 in

  let fill_map map pc out = 
    let (i, n, t) = out in
    let m = cleanup_var n in
    if (Hashtbl.mem map m) then
      Hashtbl.replace map m ((pc, out) :: (Hashtbl.find map m))
    else
      Hashtbl.add map m [(pc, out)]
  in
  let pair_pc_outs map outs pc = 
    List.iter (fun out -> fill_map map pc out) outs in
  List.iter (fun (ins, outs, pc) -> pair_pc_outs pc_outs1 outs pc) in_out_pc1;
  List.iter (fun (ins, outs, pc) -> pair_pc_outs pc_outs2 outs pc) in_out_pc2;

  assert ((keys pc_outs1) = (keys pc_outs2));

  (* fold the various (pc, out) pairs for a give output into a single ITE
     expression *)
  let ite c e1 e2 =
    let mkexp v = V.Lval (V.Temp v) in
    let c = V.Cast(V.CAST_SIGNED, V.REG_8, (mkexp c)) in
    V.exp_or (V.exp_and c (mkexp e1)) (V.exp_and (V.exp_not c) e2) in

  let foldexp map var base =
    List.fold_left (fun res (pc, out) -> ite pc out res) 
      base (Hashtbl.find map var) in

  let formulas1 = Hashtbl.create 79 in
  let formulas2 = Hashtbl.create 79 in
 
  let zero = V.Constant(V.Int(V.REG_8, 0L)) in
  let one = V.Constant(V.Int(V.REG_8, 1L)) in

  List.iter (fun out -> Hashtbl.add formulas1 out (foldexp pc_outs1 out zero)) 
    (keys pc_outs1);
  List.iter (fun out -> Hashtbl.add formulas2 out (foldexp pc_outs2 out one)) 
    (keys pc_outs2);

  assert ((keys formulas1) = (keys formulas2));

  (decls, stmts, formulas1, formulas2)


(* ===--------------------------------------------------------------------=== *)
let main argv = 
  let qe = Options_solver.construct_solver "" in
  let prog1 = Sys.argv.(1) in
  let prog2 = Sys.argv.(2) in
  assert (Sys.file_exists prog1 && Sys.is_directory prog1);
  assert (Sys.file_exists prog2 && Sys.is_directory prog2);
  let prog1 = parse_prog_paths prog1 in 
  let prog2 = parse_prog_paths prog2 in  
  let decls, stmts, formulas1, formulas2 = merge_progs prog1 prog2 in

  printf "\n\nPROG1:\n";
  Hashtbl.iter (fun k v -> printf "%s ==> %s\n" k (exp_to_string v)) formulas1;
  printf "\n\nPROG2:\n";
  Hashtbl.iter (fun k v -> printf "%s ==> %s\n" k (exp_to_string v)) formulas2;
  
  printf "\n\n";
  List.iter (fun v -> printf "%s\n" (var_to_string v)) decls;
  List.iter (fun s -> printf "%s\n" (stmt_to_string s)) stmts;

  let e1 = Hashtbl.find formulas1 (List.hd (keys formulas1)) in
  let e2 = Hashtbl.find formulas2 (List.hd (keys formulas2)) in

  (* (V.UnOp(V.NOT, check_expr)) *)
  let q = V.exp_not (V.exp_eq e1 e2) in
  let e = List.fold_left (fun acc stmt -> 
    match stmt with
      | V.Move(lval, exp) -> V.Let(lval, exp, acc)
      | _ -> assert false
  ) q (List.rev stmts) in

  printf "\n\nQUERY: %s\n" (exp_to_string e);

  qe#prepare decls [];
  qe#query e;
  qe#unprepare true;

  ()



;;

main Sys.argv;;
