module V = Vine
open Printf
open Unix

let input_variables = Hashtbl.create 79

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


let simplify i = 
  String.concat "_" (List.rev(List.tl(List.rev(
    Str.split (Str.regexp_string "_") i))))


let starts_with str pat = 
  let n = min (String.length pat) (String.length str) in
  (String.sub str 0 n) = pat


let strip str =
    Str.global_replace (Str.regexp_string "\n") "" str


let keys map =
  Hashtbl.fold (fun k v acc -> k :: acc) map []


let values map =
  Hashtbl.fold (fun k v acc -> v :: acc) map []


let var_to_string v = strip(V.var_to_string v)
let exp_to_string e = strip(V.exp_to_string e)
let stmt_to_string s = strip(V.stmt_to_string s)


let cleanup_var i = 
  String.concat "_" (List.rev(List.tl(List.rev(
    Str.split (Str.regexp_string "_") i))))


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

(* ===--------------------------------------------------------------------=== *)

let parse_prog file = 
  let prog = Vine_parser.parse_file file in
  let (decls, stmts) = prog in
  let rename_var tab var =
    let (i,n,t) = var in
    if not (Hashtbl.mem tab n) then
      Hashtbl.add tab n (V.newvar (simplify n) t);
    Hashtbl.find tab n
  in
  let invars = List.filter (fun (_,n,_) -> (starts_with n "in_")) decls in
  (* Unique map of variables (use the first occurrence) *)
  let invars = List.map (fun v -> rename_var input_variables v) invars in
  let temps = List.filter (fun (_,n,_) -> (starts_with n "t")) decls in
  let outvars = List.filter (fun (_,n,_) -> (starts_with n "out_")) decls in
  let pc = List.hd(List.filter (fun (_,n,_) -> (starts_with n "pathcond_")) 
		     decls) in
  (* Rename all input variables *)
  let stmts = List.map(fun s -> rename_var_in_stmt input_variables s) stmts in
  (invars, temps, outvars, pc, stmts)

(* ===--------------------------------------------------------------------=== *)

let merge_paths progs =
  (* map a given output to its possible values [(pc1 -> out1), (pc2 -> out2)] *)
  let pc_outs = Hashtbl.create 79 in
  let var_outs = Hashtbl.create 79 in

  let fill_map pc out = 
    let (i, n, t) = out in
    let m = cleanup_var n in
    if (Hashtbl.mem pc_outs m) then
      Hashtbl.replace pc_outs m ((pc, out) :: (Hashtbl.find pc_outs m))
    else (
      Hashtbl.add pc_outs m [(pc, out)];
      Hashtbl.add var_outs m (V.newvar m t)
    )
  in
  let pair_pc_outs map outs pc = 
    List.iter (fun out -> fill_map pc out) outs
  in

  List.iter (fun (_, _, outs, pc, _) -> pair_pc_outs pc_outs outs pc) progs;

  let zero = V.Constant(V.Int(V.REG_8, 0L)) in

  (* fold the various (pc, out) pairs for a give output into a single ITE
     expression *)
  let ite c e1 e2 =
    let mkexp v = V.Lval (V.Temp v) in
    let c = V.Cast(V.CAST_SIGNED, V.REG_8, (mkexp c)) in
    V.exp_or (V.exp_and c (mkexp e1)) (V.exp_and (V.exp_not c) e2) 
  in

  let foldexp pc_out base =
    List.fold_left (fun res (pc, out) -> ite pc out res) 
      base pc_out;
  in


  let outputs = Hashtbl.fold (fun k v acc -> ((Hashtbl.find var_outs k), 
					      (foldexp v zero)) :: acc)
    pc_outs []
  in
  
  outputs

(* ===--------------------------------------------------------------------=== *)

let def_stmt stmt = 
  match stmt with
    | V.Move(V.Temp(v), exp) -> v
    | _ -> failwith "unsupported statement"
  

let use_exp exp = 
  let vars = ref [] in
  let rec exp_loop = function
    | V.Name(s) as n -> ()
    | V.BinOp(op, e1, e2) -> exp_loop e1; exp_loop e2
    | V.UnOp(op, e1) -> exp_loop e1
    | V.Cast(ct, ty, e1) -> exp_loop e1
    | V.Lval(lv) -> lv_loop lv
    | V.Let(lv, e1, e2) ->
        lv_loop lv; exp_loop e1; exp_loop e2
    | _ as e -> ()
  and lv_loop = function
    | V.Temp(v) -> vars := v :: !vars
    | V.Mem(v, e, ty) -> exp_loop e
  in
  exp_loop exp;
  Vine_util.list_unique !vars

let use_stmt stmt =
  match stmt with
    | V.Move(lval, exp) -> use_exp exp
    | _ -> failwith "unsupported statement"
  

let slice stmts exp = 
  let vars = ref (use_exp exp) in
  let stmts = 
    List.filter(fun s ->
      let usedvars = use_stmt s in
      let defvar = def_stmt s in 
      if (List.mem defvar !vars) then (
	vars := Vine_util.list_unique (usedvars @ !vars);
	true
      ) else (
	false
      )
    ) (List.rev stmts)
  in
  List.rev stmts
  

let augment_paths decls outputs statements = 
  let outputs = List.map (
    fun (o, e) ->
      let e' = 
	List.fold_left (fun acc stmt -> 
	  match stmt with
	    | V.Move(lval, exp) -> V.Let(lval, exp, acc)
	    | _ -> failwith "unsupported statement"
	) e (List.rev (slice statements e))
      in
      (o, e')
  ) outputs in
  outputs


(* ===--------------------------------------------------------------------=== *)

let main argv = 
  let progs = List.tl (Array.to_list Sys.argv) in
  let progs = List.map (fun p -> parse_prog p) progs in
  let invars = List.fold_left (fun a (v,_,_,_,_) -> v @ a) [] progs in
  let temps = List.fold_left (fun a (_,v,_,_,_) -> v @ a) [] progs in
  let pcs = List.fold_left (fun a (_,_,_,v,_) -> v :: a) [] progs in
  let stmts = List.fold_left(fun a (_,_,_,_,s) -> s @ a) [] progs in
  let outputs = merge_paths progs in
  let outvars = List.fold_left (fun a (_,_,v,_,_) -> v @ a)
    (List.map(fun (v, e) -> v) outputs) progs in
  let decls = Vine_util.list_unique (invars @ temps @ pcs @ outvars) in
  let outputs = augment_paths decls outputs stmts in

  List.iter (fun v -> printf "var %s;\n" (var_to_string v)) decls;
  List.iter (fun (v, e) -> printf "%s = %s;\n" (var_to_string v) 
    (exp_to_string e)) outputs

;;

main Sys.argv;;
