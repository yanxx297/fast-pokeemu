(*
  Copyright (C) BitBlaze, 2011. All rights reserved.
*)

val vine_type_to_z3_sort : Z3.context -> Vine.typ -> Z3.sort

val make_named_var    : Z3.context -> Vine.var -> string -> Z3.ast
val make_numbered_var : Z3.context -> Vine.var -> Z3.ast

val vine_exp_to_z3_term :
  Z3.context -> (int, (Vine.var * Z3.ast)) Hashtbl.t -> Vine.exp -> Z3.ast

val z3_lbool_to_bool_opt : Z3.lbool -> bool option

val z3_model_to_vine_scalars : Z3.context
  -> (int, (Vine.var * Z3.ast)) Hashtbl.t
  -> (string, (Vine.var * Z3.ast)) Hashtbl.t
  -> Z3.model -> (Vine.var * int64) list

class z3vc : object
  method declare_var_numbered : Vine.var -> unit
  method declare_var : Vine.var -> unit
  method clear_vars : unit
  method trans_exp : Vine.exp -> Z3.ast
  method assert_z3_ast : Z3.ast -> unit
  method assert_exp : Vine.exp -> unit
  method exp_to_string : Vine.exp -> string
  method z3_ast_to_string : Z3.ast -> string
  method push : unit
  method pop : unit
  method reset : unit
  method query : (bool option * (Vine.var * int64) list)
  method benchmark_to_smtlib_string : string -> string -> 
    Z3.ast list -> Z3.ast -> string
end
