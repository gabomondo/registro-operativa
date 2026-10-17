"""Pantalla(s) de la app como Mixin de App (export_json, import_json, export_csv…)."""
from datetime import date, datetime
import csv
import json

from tkinter import filedialog, messagebox

from registro import db as _db
from registro.constantes import CHECK_KEYS
from registro.db import connect, db_all, db_notas_rango, db_playbooks, db_templates, init_db
from registro.ui import vivo

vivo.registrar(globals())


class DatosIOMixin:
    def export_json(self):
        rows = db_all(todo=True)
        payload = {
            "version": 3,
            "templates": db_templates(),
            "operaciones": rows,
            "playbooks": db_playbooks(),
            "notas": list(db_notas_rango("0000-01-01", "9999-12-31").values()),
        }
        path = filedialog.asksaveasfilename(defaultextension=".json",
                    initialfile=f"registro_operativa_{date.today().isoformat()}.json",
                    filetypes=[("JSON","*.json")])
        if not path: return
        with open(path,"w",encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Backup", f"Exportadas {len(rows)} operaciones y {len(payload['templates'])} plantillas.\n\nLas capturas están en la carpeta 'capturas' — respaldala junto con el .db.")

    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
        if not path: return
        try:
            with open(path,encoding="utf-8") as f: raw = json.load(f)
        except Exception:
            messagebox.showerror("Importar","Archivo inválido."); return

        # compatibilidad: backups viejos eran una lista plana de operaciones;
        # los nuevos son un dict {templates, operaciones}.
        if isinstance(raw, list):
            data = raw
            templates = []
            playbooks, notas = [], []
        elif isinstance(raw, dict) and isinstance(raw.get("operaciones"), list):
            data = raw["operaciones"]
            templates = raw.get("templates") or []
            playbooks = raw.get("playbooks") or []
            notas = raw.get("notas") or []
        else:
            messagebox.showerror("Importar","Archivo inválido."); return

        replace = messagebox.askyesnocancel("Importar",
            f"{len(data)} operaciones · {len(templates)} plantillas · {len(playbooks)} playbooks · {len(notas)} notas.\n\nSí = reemplazar todo\nNo = fusionar\nCancelar = abortar")
        if replace is None: return
        con = connect()
        if replace:
            con.execute("DELETE FROM operaciones")
            con.execute("DELETE FROM check_templates")
            con.execute("DELETE FROM playbooks")
            con.execute("DELETE FROM notas")
            con.commit()

        # 1) plantillas: insertar y construir mapa viejo_id -> nuevo_id
        tpl_map = {}
        for t in templates:
            items = t.get("items") or []
            cur = con.execute(
                "INSERT INTO check_templates (nombre, items, actualizado) VALUES (?,?,?)",
                (t.get("nombre") or "Sin nombre",
                 json.dumps(items, ensure_ascii=False),
                 datetime.now().isoformat(timespec="seconds")))
            if t.get("id") is not None:
                tpl_map[t["id"]] = cur.lastrowid
        con.commit()

        # 2) operaciones
        chk_cols = ",".join(CHECK_KEYS)
        chk_ph   = ",".join(["?"] * len(CHECK_KEYS))
        for o in data:
            chk_vals = [int(o.get(k, 0) or 0) for k in CHECK_KEYS]
            old_tpl = o.get("tpl_id")
            new_tpl = tpl_map.get(old_tpl, old_tpl if not tpl_map else None)
            chk_data = o.get("chk_data")
            if chk_data is None:
                # backup viejo sin chk_data: reconstruir de las columnas chk_*
                chk_data = json.dumps({k: int(o.get(k, 0) or 0) for k in CHECK_KEYS},
                                      ensure_ascii=False)
            elif not isinstance(chk_data, str):
                chk_data = json.dumps(chk_data, ensure_ascii=False)
            ex = list(_db.EXTRA_COLS)
            con.execute(f"""INSERT OR IGNORE INTO operaciones
                (fecha,hora,activo,tipo,profit,empresa,cuenta,mov_sl,tranquilo,emo,comentario,img_ini,img_fin,tpl_id,chk_data,{chk_cols},{",".join(ex)})
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,{chk_ph},{",".join("?" * len(ex))})""",
                (o.get("fecha"),o.get("hora"),o.get("activo"),o.get("tipo"),o.get("profit"),
                 o.get("empresa"),o.get("cuenta"),o.get("mov_sl"),o.get("tranquilo"),
                 o.get("emo"),o.get("comentario"),o.get("img_ini"),o.get("img_fin"),
                 new_tpl,chk_data,*chk_vals,
                 *[(o.get(c) if o.get(c) is not None or c != "fuente" else "manual") for c in ex]))
        # 3) playbooks y notas del notebook (las existentes no se pisan al fusionar)
        for pb in playbooks:
            con.execute("INSERT OR IGNORE INTO playbooks (nombre, descripcion, reglas, actualizado) VALUES (?,?,?,?)",
                        (pb.get("nombre"), pb.get("descripcion"), pb.get("reglas"), pb.get("actualizado")))
        for n in notas:
            con.execute("INSERT OR IGNORE INTO notas (fecha, plan, que_paso, corregir, actualizado) VALUES (?,?,?,?,?)",
                        (n.get("fecha"), n.get("plan"), n.get("que_paso"), n.get("corregir"), n.get("actualizado")))
        con.commit(); con.close()
        # asegurar plantilla original + asociar ops sin plantilla
        init_db()
        self.render_table()
        self._reload_templates_into_combo()
        self.render_plantillas()
        messagebox.showinfo("Importar","Listo. Nota: si venís de otra PC, copiá también la carpeta 'capturas'.")

    def export_csv(self):
        rows = db_all()
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                    initialfile=f"registro_operativa_{date.today().isoformat()}.csv",
                    filetypes=[("CSV","*.csv")])
        if not path: return
        cols = ["fecha","hora","activo","tipo","profit","empresa","cuenta","mov_sl","tranquilo","emo","comentario"]
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for o in rows: w.writerow(o)
        messagebox.showinfo("CSV", f"Exportadas {len(rows)} operaciones.")
