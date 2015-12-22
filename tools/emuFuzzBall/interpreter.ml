module V = Vine
open Printf

let ctx = Hashtbl.create 79

let starts_with str pat = 
  let n = min (String.length pat) (String.length str) in
  (String.sub str 0 n) = pat


(* use name + id for everything that is not an input var (otherwise collisions
   can happen when using externally loaded symbolic expressions) *)
let mkvar (i,n,_) = 
  if (starts_with n "in_") || (starts_with n "mem_") then
    n
  else
    n ^ "_" ^ (string_of_int i)


let ctx_reset () =
  Hashtbl.clear ctx


let ctx_mem variable = 
  Hashtbl.mem ctx variable


let ctx_set (variable:string) (value:int64) =
  if (Hashtbl.mem ctx variable) then (
    printf "%s already defined\n" variable;
    assert (false)
  );
  Hashtbl.add ctx variable value


let ctx_get variable =
  if not (Hashtbl.mem ctx variable) then (
    printf "%s not found!\n" variable
  );
  Hashtbl.find ctx variable
    
    
let ctx_del variable = 
  Hashtbl.remove ctx variable


let ctx_mem variable =
  Hashtbl.mem ctx variable


let ctx_init vv =
  ctx_reset ();
  List.iter (fun (v, v') -> ctx_set v v') vv


let ctx_dump () =
  printf "***************** CTX ***************\n";
  Hashtbl.iter (fun k v -> printf "%s  -->  %Lx\n" k v) ctx;
  printf "*************************************\n"


let eval_var v = 
  match v with
    | V.Temp(v) -> ctx_get (mkvar v)
    | V.Mem(v,V.Constant(V.Int(_,i)),_) -> 
			(*Printf.printf "eval result: 0x%08Lx\n" (ctx_get (sprintf "mem_byte_0x%08Lx" i));
      printf "V: %s I:%08Lx\n" (V.var_to_string v)  i;
      failwith "mem?"*)
      printf "V: %s I:%08Lx\n" (V.var_to_string v)  i;
      ctx_get (sprintf "mem_byte_0x%08Lx" i) 
    | _ -> failwith "unsupported lval expr"


let eval_exp e =
  let cf_eval e =
    match Vine_opt.constant_fold (fun _ -> None) e with
      | V.Constant(V.Int(_, _)) as c -> c
      | e ->
	printf "Left with %s\n" (V.exp_to_string e);
	failwith "cf_eval failed in eval_expr"
  in
  let rec loop e =
    match e with
      | V.BinOp(op, e1, e2) -> cf_eval (V.BinOp(op, loop e1, loop e2))
      | V.UnOp(op, e1) -> cf_eval (V.UnOp(op, loop e1))
      | V.Cast(op, ty, e1) -> cf_eval (V.Cast(op, ty, loop e1))
      | V.Constant(V.Int(_, _)) -> e
      | V.Lval(V.Mem(_, a, ty) as lv) ->
	let v = eval_var lv in
	V.Constant(V.Int(ty, v))
      | V.Lval(V.Temp(_, _,ty) as lv) ->
	let v = eval_var lv in
	V.Constant(V.Int(ty, v))
      | V.Let(V.Temp(v), e1, e2) ->
	let c = 
	  match (cf_eval (loop e1)) with 
	    | V.Constant(V.Int(_, i64)) -> i64
	    | _ -> failwith "Constant invariant failed in cf_eval"
	in
	ctx_set (mkvar v) c;
	cf_eval (loop e2)
      | _ ->
	printf "Can't evaluate %s\n" (V.exp_to_string e);
	failwith "Unexpected expr in eval_expr"
  in
  match loop e with
    | V.Constant(V.Int(_, i64)) -> i64
    | e ->
      printf "Left with %s\n" (V.exp_to_string e);
      failwith "Constant invariant failed in eval_expr"


let eval_assgn v e =
	ctx_set v (eval_exp e)
	(*(match e with
	| V.Lval(V.Temp(_)) -> ctx_set v (eval_exp e)
	| _ -> ()) *)
  
    

let eval_assgns vvee =
  List.iter (fun (v, e) -> eval_assgn (mkvar v) e) vvee

