module V = Vine
open Printf
open Unix

let starts_with str pat = 
  let n = min (String.length pat) (String.length str) in
  (String.sub str 0 n) = pat

let split_string char s =
  let delim_loc = String.index s char in
  let s1 = String.sub s 0 delim_loc in
  let s2 = String.sub s (delim_loc + 1) ((String.length s) - delim_loc - 1)
  in
    (s1, s2)

let strip str =
  Str.global_replace (Str.regexp_string "\n") "" str

let var_to_string v = strip(V.var_to_string v)
let exp_to_string e = strip(V.exp_to_string e)
let stmt_to_string s = strip(V.stmt_to_string s)

let simplify i = 
  String.concat "_" (List.rev(List.tl(List.rev(
    Str.split (Str.regexp_string "_") i))))

let simplify2 i = 
  String.concat "_" (List.rev(List.tl(List.tl(List.rev(
    Str.split (Str.regexp_string "_") i)))))

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


let main argv = 
  let prog = ref "" in
  let ctx = ref [] in

  Arg.parse (Arg.align ([
    ("-prog", Arg.String (fun s -> prog := s),
     "prog Program to use");
    ("-ctx", Arg.String (fun s -> 
      let n,v = split_string '=' s in
      ctx := (n, Int64.of_string v) :: !ctx),
     "var=val Initial value for variable");
  ])) (fun arg -> () ) "invalid argument";

  let (decls, stmts) = Vine_parser.parse_file !prog in
  Vine_typecheck.typecheck (decls, stmts);
  let invars = List.filter (fun (i,n,v) -> starts_with n "in_") decls in
  let outvars = List.filter (fun (i,n,v) -> starts_with n "out_") decls in
  let newvars = Hashtbl.create (List.length decls) in
  List.iter (fun v -> 
    let (i,n,t) = v in
    Hashtbl.add newvars n (V.newvar (simplify n) t)) invars;
  List.iter (fun v -> 
    let (i,n,t) = v in
    Hashtbl.add newvars n (V.newvar (simplify n) t)) outvars;
  let decls = List.map (fun v -> rename_var_in_decl newvars v) decls in
  let stmts = List.map (
    fun s ->
      match s with 
	| V.Move(V.Temp(v), e) -> (v, e)
	| _ -> failwith "unexpected statement"
  ) (List.map (fun s -> rename_var_in_stmt newvars s) stmts) in

  List.iter (fun ((_, n, _), e) -> 
    (* reinit the context each time because everything in inlined in the
       statement *)
    Interpreter.ctx_init !ctx;
    printf "%s=%02Lx\n" n (Interpreter.eval_exp e);
  ) stmts;

  ()
;;

main Sys.argv;;
