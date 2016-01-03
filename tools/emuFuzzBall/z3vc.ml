(*
  Copyright (C) BitBlaze, 2011. All rights reserved.
*)

module V = Vine;;

let vine_type_to_z3_sort ctx = function
  | V.REG_1 -> Z3.mk_bool_sort ctx
  | V.REG_8  -> Z3.mk_bv_sort ctx  8
  | V.REG_16 -> Z3.mk_bv_sort ctx 16
  | V.REG_32 -> Z3.mk_bv_sort ctx 32
  | V.REG_64 -> Z3.mk_bv_sort ctx 64
  | _ -> failwith "Unsupported type in vine_type_to_z3_sort"

let make_named_var ctx (_,_,ty) s =
  Z3.mk_const ctx (Z3.mk_string_symbol ctx s) (vine_type_to_z3_sort ctx ty)

let make_numbered_var ctx (n,_,ty) =
  Z3.mk_const ctx (Z3.mk_int_symbol ctx n) (vine_type_to_z3_sort ctx ty)

let vine_exp_to_z3_term ctx vnm e =
	Printf.printf "%s\n" (V.exp_to_string e);
  let bindings = V.VarHash.create 101 in
  let rec loop = function
    | V.Constant(V.Int(V.REG_1, b)) ->
	((if b = 0L then Z3.mk_false else Z3.mk_true) ctx, V.REG_1)
    | V.Constant(V.Int((V.REG_8|V.REG_16) as ty, v)) ->
	(Z3.mk_int ctx (Int64.to_int v) (vine_type_to_z3_sort ctx ty), ty)
    | V.Constant(V.Int((V.REG_32|V.REG_64) as ty, v)) ->
	(Z3.mk_numeral ctx (Int64.to_string v) (vine_type_to_z3_sort ctx ty),
	 ty)
    | V.Constant(_) -> failwith "Unexpected constant type"
    | V.UnOp(op, e1) ->
	let (z1, ty1) = loop e1 in
	let constr =
	  match (op, ty1) with
	    | (V.NOT, V.REG_1) -> Z3.mk_not
	    | (V.NOT, _      ) -> Z3.mk_bvnot
	    | (V.NEG, V.REG_1) -> Z3.mk_not
	    | (V.NEG, _      ) -> Z3.mk_bvneg
	in
	  ((constr ctx z1), ty1)
    | V.BinOp((V.LSHIFT|V.RSHIFT|V.ARSHIFT) as op, e1, e2) ->
	let (z1, ty1) = loop e1 in
	  let width_cvt t1 t2 e = 
	    let wd1 = V.bits_of_width t1 and
		wd2 = V.bits_of_width t2 in
	      if wd1 = wd2 then
		e
	      else if wd1 < wd2 then
		V.Cast(V.CAST_UNSIGNED, t2, e)
	      else
		V.Cast(V.CAST_LOW, t2, e)
	  in
	  let e2' = width_cvt (Vine_typecheck.infer_type_fast e2) ty1 e2 in
	  let (z2, ty2) = loop e2' in
	    assert(ty1 = ty2);
	    let z' =
	      match (op, ty1) with
		| (V.LSHIFT, V.REG_1)
		| (V.RSHIFT, V.REG_1) ->
		    Z3.mk_and ctx [|z1; Z3.mk_not ctx z2|]
		| (V.ARSHIFT, V.REG_1) -> Z3.mk_false ctx
		| (V.LSHIFT,  _) -> Z3.mk_bvshl  ctx z1 z2
		| (V.RSHIFT,  _) -> Z3.mk_bvlshr ctx z1 z2
		| (V.ARSHIFT, _) -> Z3.mk_bvashr ctx z1 z2
		| (_, _) -> failwith "Can't happen: non-shift in shift case"
	    in
	      (z', ty1)
    | V.BinOp(op, e1, e2) ->
	let (z1, ty1) = loop e1 and
	    (z2, ty2) = loop e2 in
	let binify f = fun ctx a b -> f ctx [|a; b|] in
	let nfirst f = fun ctx a b -> f ctx (Z3.mk_not ctx a) b in
	let nsecond f = fun ctx a b -> f ctx a (Z3.mk_not ctx b) in
	let constr =
	  match (op, ty1) with
	    | (V.PLUS,    V.REG_1) -> Z3.mk_xor
	    | (V.PLUS,    _      ) -> Z3.mk_bvadd
	    | (V.MINUS,   V.REG_1) -> Z3.mk_eq
	    | (V.MINUS,   _      ) -> Z3.mk_bvsub
	    | (V.TIMES,   V.REG_1) -> binify Z3.mk_and
	    | (V.TIMES,   _      ) -> Z3.mk_bvmul
	    | (V.DIVIDE,  V.REG_1) -> Z3.mk_eq
	    | (V.DIVIDE,  _      ) -> Z3.mk_bvudiv
	    | (V.SDIVIDE, V.REG_1) -> Z3.mk_eq
	    | (V.SDIVIDE, _      ) -> Z3.mk_bvsdiv
	    | (V.MOD,     V.REG_1) -> Z3.mk_eq
	    | (V.MOD,     _      ) -> Z3.mk_bvurem
	    | (V.SMOD,    V.REG_1) -> Z3.mk_eq
	    | (V.SMOD,    _      ) -> Z3.mk_bvsmod
	    | (V.BITAND,  V.REG_1) -> binify Z3.mk_and
	    | (V.BITAND,  _      ) -> Z3.mk_bvand
	    | (V.BITOR,   V.REG_1) -> binify Z3.mk_or
	    | (V.BITOR,   _      ) -> Z3.mk_bvor
	    | (V.XOR,     V.REG_1) -> Z3.mk_xor
	    | (V.XOR,     _      ) -> Z3.mk_bvxor
	    | (V.EQ,      _      ) -> Z3.mk_eq
	    | (V.NEQ,     _      ) -> binify Z3.mk_distinct
	    | (V.LT,      V.REG_1) -> nfirst (binify Z3.mk_and)
	    | (V.LT,      _      ) -> Z3.mk_bvult
	    | (V.LE,      V.REG_1) -> nfirst (binify Z3.mk_or)
	    | (V.LE,      _      ) -> Z3.mk_bvule
	    | (V.SLT,     V.REG_1) -> nsecond (binify Z3.mk_and)
	    | (V.SLT,     _      ) -> Z3.mk_bvslt
	    | (V.SLE,     V.REG_1) -> nsecond (binify Z3.mk_or)
	    | (V.SLE,     _      ) -> Z3.mk_bvsle
	    | ((V.LSHIFT|V.RSHIFT|V.ARSHIFT), _) ->
		failwith "Shifts should have been the case above"
	in
	let ty = match op with
	  | (V.EQ|V.NEQ|V.LT|V.LE|V.SLT|V.SLE) -> V.REG_1
	  | _ -> ty1 in
	  ((constr ctx z1 z2), ty)
    | V.Cast(ct, ty2, e1) ->
	let (z1, ty1) = loop e1 in
	let (wd1, wd2) = (Vine.bits_of_width ty1, Vine.bits_of_width ty2) in
	let z2 =
	  if wd1 = wd2 then z1 else
	    let z1' = if ty1 <> V.REG_1 then z1 else
	      Z3.mk_ite ctx z1
		(Z3.mk_int ctx 1 (Z3.mk_bv_sort ctx 1))
		(Z3.mk_int ctx 0 (Z3.mk_bv_sort ctx 1))
	    in
	      match ct with
		| V.CAST_UNSIGNED ->
		    assert(wd2 > wd1);
		    Z3.mk_zero_ext ctx (wd2 - wd1) z1'
		| V.CAST_SIGNED ->
		    assert(wd2 > wd1);
		    Z3.mk_sign_ext ctx (wd2 - wd1) z1'
		| V.CAST_LOW ->
		    assert(wd2 < wd1);
		    Z3.mk_extract ctx (wd2 - 1) 0 z1'
		| V.CAST_HIGH ->
		    assert(wd2 < wd1);
		    Z3.mk_extract ctx (wd1 - 1) (wd1 - wd2) z1'
	in
	let z2' = if ty2 <> V.REG_1 then z2 else
	  Z3.mk_eq ctx z2 (Z3.mk_int ctx 1 (Z3.mk_bv_sort ctx 1))
	in
	  (z2', ty2)
    | V.Let(V.Temp(var), e1, e2) ->
	(* We translate away Lets, but it doesn't cause a size explosion
	   because Z3 will properly share the subtrees. *)
	let (z1, _) = loop e1 in
	  V.VarHash.add bindings var z1;
	  let (z2, ty2) = loop e2 in
	    V.VarHash.remove bindings var;
	    (z2, ty2)
    | V.Lval(V.Temp((n,_,ty) as var)) ->
	(try
	   ((V.VarHash.find bindings var), ty)
	 with Not_found ->	  
	   let (_, z3) = Hashtbl.find vnm n in
	     (z3, ty))
    | V.Lval(V.Mem(_, _, _))
    | V.Let(V.Mem(_, _, _), _, _) ->
	failwith "Arrays unimplemented in Z3 translation"
    | V.Unknown(_) -> failwith "Unknowns not handled in Z3 translation"
    | V.Name(_) -> failwith "Unknowns not handled in Z3 translation"
  in
  let (z, _) = loop e in
    z

let z3_lbool_to_bool_opt = function
  | Z3.L_FALSE -> Some false
  | Z3.L_TRUE -> Some true
  | Z3.L_UNDEF -> None

let z3_model_to_vine_scalars ctx vnm vsm m =
  Array.to_list
    (Array.map
       (fun e ->
	  let (sym, (ok, rhs)) =
	    ((Z3.get_decl_name ctx e), (Z3.eval_func_decl ctx m e)) in
	    assert(ok);
	    let var = match Z3.symbol_refine ctx sym with
	     | Z3.Symbol_int i ->
		 let (var, _) = Hashtbl.find vnm i in
		   var
	     | Z3.Symbol_string s ->
		 let (var, _) = Hashtbl.find vsm s in
		   var
	     | _ -> failwith "Unexpected symbol type in model"
	    in
	    let rhs_v = 
	      match Z3.term_refine ctx rhs with
		| Z3.Term_numeral(nm, sort) ->
		    (match Z3.sort_refine ctx sort with
		       | Z3.Sort_bv wd ->
			   (match nm with
			      | Z3.Numeral_small(n, 1L) -> n
			      | Z3.Numeral_large(s) ->
				  let n = Int64.of_string s in
				  let s' = Int64.to_string n in
				    assert(s = s');
				    n
			      | _ -> failwith "Unexpected BV numeral")
		       | _ -> failwith "Unexpected sort in print_model")
		| Z3.Term_app(Z3.OP_TRUE, _, [||]) -> 1L
		| Z3.Term_app(Z3.OP_FALSE, _, [||]) -> 0L
		| _ -> failwith "Unexpected AST in print_model"
	    in
	      (var, rhs_v))
       (Z3.get_model_constants ctx m))

class z3vc = object(self)
  val ctx =
    let ctx = Z3.mk_context_x [|("MODEL", "true")|] in
      Z3.push ctx;
      ctx

  val var_num_map = Hashtbl.create 101
  val var_str_map = Hashtbl.create 101

  method declare_var_numbered ((n,(_:string),_) as var) =
    Hashtbl.replace var_num_map n (var, (make_numbered_var ctx var))

  val unique_names = Hashtbl.create 101

  method private unique_name ((n,s,_) as var) =
    try
      let v1 = Hashtbl.find unique_names s in
	if v1 = var then s
	else
	  s ^ "?" ^ (string_of_int n)
    with Not_found ->
      Hashtbl.replace unique_names s var;
      s

  method declare_var ((n,_,_) as var) =
    let s = self#unique_name var in
    let z3 = make_named_var ctx var s in
      Hashtbl.replace var_num_map n (var, z3);
      Hashtbl.replace var_str_map s (var, z3);

  method clear_vars =
    Hashtbl.clear var_num_map;
    Hashtbl.clear unique_names

  method trans_exp e =
    vine_exp_to_z3_term ctx var_num_map e

  method assert_z3_ast = Z3.assert_cnstr ctx

  method assert_exp e =
    self#assert_z3_ast (self#trans_exp e)

  method exp_to_string e =
    Z3.ast_to_string ctx (self#trans_exp e)

  method z3_ast_to_string = Z3.ast_to_string ctx

  method push = Z3.push ctx

  method pop = Z3.pop ctx 1

  method reset =
    self#clear_vars;
    Z3.pop ctx (Z3.get_num_scopes ctx);
    Z3.push ctx

  method query =
    let (lb, m) = Z3.check_and_get_model ctx in
    let vm = match lb with
      | Z3.L_FALSE -> []
      | _ -> z3_model_to_vine_scalars ctx var_num_map var_str_map m
    in
      Z3.del_model ctx m;
      ((z3_lbool_to_bool_opt lb), vm)

  method benchmark_to_smtlib_string name status assumptions form =
    (* let ctx_s = Z3.context_to_string ctx in *)
    let bmark = 
      Z3.benchmark_to_smtlib_string ctx name "QF_BV" status ""
	(Array.of_list assumptions) form
    in
      (* "; " ^ ctx_s ^ "\n" ^ *) bmark
end

