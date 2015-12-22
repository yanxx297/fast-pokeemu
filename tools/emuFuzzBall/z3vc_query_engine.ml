(*
  Copyright (C) BitBlaze, 2011. All rights reserved.
*)

module V = Vine;;

open Exec_options;;
open Query_engine;;

class z3vc_engine = object(self)
  inherit query_engine

  val vc = new Z3vc.z3vc

  method start_query =
    ()

  method add_free_var var =
    vc#declare_var var

  method add_temp_var var =
    vc#declare_var var

  val mutable asserts = []
  val mutable the_query = None
  val mutable status = "unknown"

  method assert_eq var rhs =
    let form = V.BinOp(V.EQ, V.Lval(V.Temp(var)), rhs) in
    let z3_form = vc#trans_exp form in
      vc#assert_z3_ast z3_form;
      asserts <- z3_form :: asserts

  method add_condition form =
    let z3_form = vc#trans_exp form in
      vc#assert_z3_ast z3_form;
      asserts <- z3_form :: asserts

  method query e =
    let e_z3 = vc#trans_exp e in
      vc#push;
      vc#assert_z3_ast e_z3;
      the_query <- Some e_z3;
      let (r_sat, m) = vc#query in
      let ce = List.map (fun ((_,s,_), v) -> (s, v)) m in
      let (r_valid, status_str) =
	(match r_sat with
	   | None -> (None, "unknown")
	   | Some true -> (Some false, "sat")
	   | Some false -> (Some true, "unsat"))
      in
	vc#pop;
	status <- status_str;
	(r_valid, (Query_engine.ce_from_list ce))

  method push =
    vc#push

  method pop =
    vc#pop

  val mutable filenum = 0

  method private print_own_lines oc =
    (* TODO: add proper declarations and formatting around these to get
       Z3 input that is legal and maximally human-readable. *)
    List.iter (fun a -> Printf.fprintf oc "%s\n" (vc#z3_ast_to_string a))
      (List.rev asserts);
    match the_query with
      | Some q -> Printf.fprintf oc "%s\n" (vc#z3_ast_to_string q)
      | None -> Printf.fprintf oc "(No query?)\n"

  method private print_using_z3 oc =
    let q = match the_query with
      | Some q -> q
      | None -> failwith "Can't print_using_z3 without a query"
    in
      Printf.fprintf oc "%s\n"
	(vc#benchmark_to_smtlib_string ("fuzz" ^ (string_of_int filenum))
	   status (List.rev asserts) q)

  method after_query save_results =
    if save_results || !opt_save_solver_files then
      (filenum <- filenum + 1;
       let fname = "fuzz-z3vc-" ^ (string_of_int filenum) ^ ".smt" in
       let oc = open_out fname in
	 if false then
	   self#print_own_lines oc
	 else
	   self#print_using_z3 oc;
	 close_out oc;
	 Printf.printf "Saved Z3 (SMT1.2) benchmark in %s\n%!" fname);

  method reset =
    asserts <- [];
    the_query <- None;
    vc#reset
end

    
      
	   
    
