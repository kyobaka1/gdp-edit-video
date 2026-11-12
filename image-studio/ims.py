"""GDP Image Studio — phủ chữ / logo / nhãn theo nhận diện shop lên ảnh listing ĐÃ XOÁ CHỮ TRUNG (lớp HTML trên ảnh).

  python ims.py kit sync <shop> [--listing <id>]     # lấy brand kit + logo + watermark của shop từ app (1 lần / khi đổi)
  python ims.py kit show <shop>                      # bộ nhận diện đang dùng cho ảnh
  python ims.py kit demo <shop>                      # ảnh mẫu mọi khối của shop trên nền tối + sáng
  python ims.py pull <listing_id>                    # tải ảnh sạch + ảnh Trung gốc + ngữ cảnh → jobs/listing-<id>/
  python ims.py new <job> --shop <shop> <ảnh…> [--kind cover] [--src <ảnh Trung gốc…>]   # job từ ảnh có sẵn trên máy
  python ims.py grid <job> [key…]                    # ảnh sạch + lưới toạ độ % + vùng trống (để chọn x, y, keep)
  python ims.py render <job> [key…]                  # layout.json → out/<key>.jpg + QA (qa/<key>.jpg, qa/<key>.json)
  python ims.py sheet <job>                          # ảnh so: Trung gốc | sạch | final
  python ims.py board <job>                          # tấm trình duyệt: cả bộ ảnh FINAL xếp hàng ngang (gửi Sếp)
  python ims.py push <job> [key…] --yes [--review]   # nộp ảnh final lên app (GHI ĐÈ kết quả) — chỉ khi Sếp đã duyệt

Quy trình + luật: skill `gdp-image-listing` (.claude/skills/gdp-image-listing/SKILL.md)."""

import argparse
import json
import shutil
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from imslib import JOBS, KINDS, SHOPS, app, kit, tools  # noqa: E402

IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}
SCHEMA = "gdp_image_layout@1"


def job_dir(name: str, must_exist: bool = True) -> Path:
    d = JOBS / name
    if must_exist and not (d / "job.json").is_file():
        raise SystemExit(f"Không có job '{name}' trong {JOBS} — tạo bằng `ims.py pull <listing_id>` hoặc `ims.py new`.")
    return d


def load(job: Path) -> tuple[dict, dict]:
    meta = json.loads((job / "job.json").read_text(encoding="utf-8"))
    layout = json.loads((job / "layout.json").read_text(encoding="utf-8"))
    return meta, layout


def save(path: Path, doc: dict) -> None:
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def seed_layout(job: Path, meta: dict) -> None:
    """Tạo / bổ sung layout.json: mỗi ảnh một khung rỗng để điền khối. Ảnh đã có layout thì giữ nguyên."""
    path = job / "layout.json"
    layout = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"schema": SCHEMA, "shop": meta["shop"], "images": {}}
    for key in [k for k in layout["images"] if k not in meta["images"] and not layout["images"][k].get("blocks")]:
        layout["images"].pop(key)                         # ảnh không thuộc job nữa (vd phần "giữ nguyên") và chưa làm gì
    for key, im in meta["images"].items():
        if im.get("clean"):
            spec = layout["images"].setdefault(key, {"kind": im["kind"], "base": im["clean"], "keep": [], "blocks": []})
            if not spec["blocks"] and (im.get("plan") or {}).get("text_blocks"):
                spec["blocks"], spec["_nhap_tu_plan"] = plan_blocks(im["plan"]["text_blocks"]), True
    save(path, layout)


def plan_blocks(text_blocks: list) -> list:
    """Chữ đã soạn sẵn trên app (design plan của skill gdp-listing-plan) → khối NHÁP. Vị trí trong plan chỉ áng chừng:
    phải soát bằng mắt + chỉnh x / y / size trước khi coi là xong."""
    kinds = {"headline": "headline", "subheadline": "sub", "badge": "badge"}
    anchors = {"top-left", "top-center", "top-right", "center-left", "center", "center-right", "bottom-left", "bottom-center", "bottom-right"}
    out = []
    for tb in text_blocks:
        if not (tb.get("text") or "").strip():
            continue
        t = kinds.get(tb.get("role"), "text")
        b = {"id": tb.get("id") or f"{t}{len(out) + 1}", "type": t, "text": tb["text"].strip(), "x": tb.get("x_pct", 50),
             "y": tb.get("y_pct", 50), "anchor": tb.get("anchor") if tb.get("anchor") in anchors else "center"}
        if tb.get("font_size_pt"):
            b["size"] = tb["font_size_pt"]
        if tb.get("width_pct") and t != "badge":
            b["w"] = tb["width_pct"]
        if tb.get("max_lines"):
            b["lines"] = tb["max_lines"]
        if tb.get("all_caps"):
            b["caps"] = True
        if t == "text":
            b["bold"] = True
        out.append(b)
    return out


# ----------------------------- kit -----------------------------
def cmd_kit(a):
    if a.action == "sync":
        p = kit.sync(a.shop, a.listing)
        print(f"✓ đã đồng bộ brand kit của {a.shop} từ app → {p}")
    if a.action == "demo":
        d = tools.kit_demo(a.shop)
        print(f"✓ ảnh mẫu khối: {d}")
        print(f"✓ ảnh so bộ font: {d.with_name('_fonts.jpg')}")
        return
    t = kit.load(a.shop)
    print(f"Shop {t['shop']} — thương hiệu {t['brand']} (kit lấy từ: {t['kit_from'] or 'CHƯA có — chạy `ims.py kit sync`'})")
    print(f"  giọng văn : {t['tone_of_voice'] or '—'}")
    print(f"  kiểu bìa  : {t['cover_style']}")
    for n, s in t["font"]["sets"].items():
        print(f"  bộ font   : {n:<10}{' (mặc định)' if n == t['font']['default'] else '':<12} chữ lớn {s['display'].name} · "
              f"chữ thường {s['body'].name} — {kit.FONT_SETS[n]['note']}")
    print(f"  màu       : " + " · ".join(f"{k} {v}" for k, v in t["color"].items()))
    b = t["badge"]
    print(f"  nhãn      : nền {b['bg']} đục {b['opacity']:.0%}{' (dải màu)' if b['gradient'] else ''} · chữ {b['text']} · viền {b['border'] or 'không'}")
    place = t["image"].get("logo_placement") or t["logo"]["placement"]
    width = t["image"].get("logo_width_pct") or t["logo"]["width_pct"]
    print(f"  logo      : {place}, rộng {width:g}% (cả khoảng đệm của file) · file: " + ", ".join(f"{k}={v.name}" for k, v in t["logo"]["files"].items()))
    print(f"  watermark : {t['watermark']['file'].name if t['watermark']['file'] else 'không có ảnh'}"
          f" · độ đục mặc định {t['watermark']['opacity']:g} (0–1, đã nhân hệ số làm mờ {t['image']['watermark_fade']:g})"
          f" · bào mảnh nét {t['image']['watermark_thin']:g}")
    for k, v in (t["rules"] or {}).items():
        if v:
            print(f"  luật chữ {k}: {v}")
    print(f"  riêng cho ảnh (shop.json → image): {json.dumps(t['image'], ensure_ascii=False)}")


# ----------------------------- new / pull -----------------------------
def cmd_new(a):
    kit.shop_dir(a.shop)
    job = job_dir(a.job, must_exist=False)
    (job / "clean").mkdir(parents=True, exist_ok=True)
    meta = json.loads((job / "job.json").read_text(encoding="utf-8")) if (job / "job.json").is_file() else {
        "job": a.job, "shop": a.shop, "listing_id": None, "name": a.name or a.job, "images": {}}
    srcs = [Path(s) for s in a.src or []]
    for i, f in enumerate(Path(x) for x in a.images):
        if not f.is_file() or f.suffix.lower() not in IMG_EXT:
            raise SystemExit(f"Không phải ảnh: {f}")
        key = f.stem
        shutil.copy2(f, job / "clean" / f.name)
        im = {"kind": a.kind, "clean": f"clean/{f.name}", "src": None, "item_id": None}
        if i < len(srcs):
            (job / "src").mkdir(exist_ok=True)
            shutil.copy2(srcs[i], job / "src" / srcs[i].name)
            im["src"] = f"src/{srcs[i].name}"
        meta["images"][key] = im
    save(job / "job.json", meta)
    seed_layout(job, meta)
    print(f"✓ job {a.job} ({a.shop}): {len(meta['images'])} ảnh → {job}")
    print(f"  tiếp: python ims.py grid {a.job}  → điền {job / 'layout.json'}  → python ims.py render {a.job}")


def cmd_pull(a):
    data = app.listing(a.listing_id)
    shop = (data.get("shop") or {}).get("name") or ""
    kit.shop_dir(shop)
    if a.sync_kit or not (SHOPS / shop / "image" / "kit.json").is_file():
        kit.sync(shop, data=data)
        print(f"  ✓ đồng bộ brand kit {shop} từ app")
    job = job_dir(a.job or f"listing-{a.listing_id}", must_exist=False)
    job.mkdir(parents=True, exist_ok=True)
    old = json.loads((job / "job.json").read_text(encoding="utf-8")) if (job / "job.json").is_file() else {"images": {}}
    plan = (app.design_plan(a.listing_id) or {}).get("items") or {}
    items = [it for kind in KINDS for it in (data.get("items") or {}).get(kind, [])]
    # PHẠM VI GIAO VIỆC: listing "Cải tiến" (update) chỉ giao một số phần — phần "Giữ nguyên" dùng ảnh đang có trên sàn,
    # KHÔNG làm, KHÔNG đụng. Listing mới = làm mọi phần ảnh.
    scope = data.get("scope") or {}
    sections = {sec["kind"]: sec for sec in scope.get("sections") or []}
    if scope.get("is_update") and sections:
        assigned = [k for k, sec in sections.items() if sec.get("enabled")]
        kept = [sec.get("label") or k for k, sec in sections.items() if not sec.get("enabled")]
    else:
        assigned, kept = list(KINDS) + ["name", "description"], []
    kinds = set(a.kind or KINDS) & set(assigned)
    if a.kind and set(a.kind) - set(assigned):
        print(f"  ⚠ phần KHÔNG được giao (giữ nguyên) nên bỏ qua: {', '.join(KINDS[k] for k in set(a.kind) - set(assigned))}")
    sources = [it for it in items if it.get("source_asset_id") and not it.get("has_result")]
    used, images, waiting = set(), {}, []

    for it in items:
        if it["kind"] not in kinds or it.get("inherited"):
            continue
        key = str(it["id"])
        if not it.get("has_result"):
            if a.allow_source and it.get("source_url"):          # ảnh gốc vốn không có chữ → dùng thẳng làm nền
                images[key] = {"kind": it["kind"], "item_id": it["id"], "position": it.get("position", 0),
                               "_clean_url": it["source_url"], "_src_url": None, "src_item": it["id"], "edited_in_app": False}
            continue
        if it.get("source_url"):                                  # cùng 1 item vừa có gốc vừa có kết quả
            src_it = it
        else:                                                     # item kết quả tách riêng → ghép với item gốc cùng loại, cùng vị trí
            cand = [s for s in sources if s["kind"] == it["kind"] and s["id"] not in used]
            src_it = next((s for s in cand if s.get("position") == it.get("position")), cand[0] if cand else None)
        if src_it:
            used.add(src_it["id"])
        images[key] = {"kind": it["kind"], "item_id": it["id"], "position": it.get("position", 0),
                       "_clean_url": it["result_url"], "_src_url": (src_it or {}).get("source_url"),
                       "src_item": (src_it or {}).get("id"), "edited_in_app": bool(it.get("has_render_state")),
                       "status": it.get("status"), "admin_note": it.get("admin_note") or "", "review_note": it.get("review_note") or "",
                       "variant_id": it.get("listing_variant_id")}
    for s in sources:
        if s["id"] not in used and s["kind"] in kinds and str(s["id"]) not in images:
            waiting.append(s["id"])

    n_new = 0
    for key, im in images.items():
        prev = old["images"].get(key) or {}
        if prev.get("clean") and (job / prev["clean"]).is_file() and not a.refresh:
            im["clean"], im["src"] = prev["clean"], prev.get("src")       # đã tải → giữ (ảnh trên app có thể đã bị ghi đè bằng final)
            im["pushed"] = prev.get("pushed")
        else:
            p = app.download(im["_clean_url"], job / "clean" / key)
            if not p:
                print(f"  ! không tải được ảnh sạch item {key}")
                continue
            im["clean"] = f"clean/{p.name}"
            s = app.download(im["_src_url"], job / "src" / key) if im["_src_url"] else None
            im["src"] = f"src/{s.name}" if s else None
            n_new += 1
        sid = str(im.get("src_item") or key)
        im["plan"] = plan.get(sid) or plan.get(key)                       # chữ đã soạn sẵn trên app (design plan) cho ảnh này
        for k in ("_clean_url", "_src_url"):
            im.pop(k, None)
    images = {k: v for k, v in images.items() if v.get("clean")}

    variants = {v["id"]: v for v in data.get("variants") or []}
    for im in images.values():
        v = variants.get(im.get("variant_id"))
        if v:
            im["variant"] = {"sku": v.get("sku"), "name": v.get("custom_name") or v.get("option_label") or v.get("name")}
    meta = {"job": job.name, "shop": shop, "listing_id": a.listing_id, "name": data.get("name", ""), "images": images,
            "waiting_clean": waiting, "listing_type": data.get("listing_type"), "assigned": assigned, "kept": kept}
    save(job / "job.json", meta)
    seed_layout(job, meta)
    brief = {"listing_id": a.listing_id, "shop": shop, "listing_type": data.get("listing_type"), "assigned_sections": assigned,
             "kept_sections": kept, "name": data.get("name", ""), "description": data.get("description", ""),
             "variants": [{"sku": v.get("sku"), "name": v.get("custom_name") or v.get("option_label") or v.get("name")}
                          for v in data.get("variants") or []],
             "section_notes": data.get("section_notes") or {}, "design_plan_overview": (app.design_plan(a.listing_id) or {}).get("overview"),
             "item_comments": data.get("item_comments") or {}}
    save(job / "brief.json", brief)

    print(f"✓ pull listing {a.listing_id} — {data.get('name', '')[:70]}")
    if kept:
        print(f"  listing CẢI TIẾN — được giao: {', '.join(sections[k].get('label') or k for k in assigned) or '(không phần nào)'}")
        print(f"                    GIỮ NGUYÊN (không làm): {', '.join(kept)}")
    print(f"  shop {shop} · {len(images)} ảnh sạch ({n_new} mới tải) → {job}")
    for kind, label in KINDS.items():
        ks = [k for k, v in images.items() if v["kind"] == kind]
        if ks:
            print(f"  {label:<14}: {', '.join(ks)}")
    ed = [k for k, v in images.items() if v.get("edited_in_app")]
    if ed:
        print(f"  ⚠ {len(ed)} ảnh đã qua Editor trên app (có thể ĐÃ có chữ, không phải ảnh sạch) — soát bằng `ims.py sheet`: {', '.join(ed)}")
    if waiting:
        print(f"  ⏳ {len(waiting)} ảnh gốc chưa có bản sạch (nhân sự chưa xoá chữ / chưa upload): {', '.join(map(str, waiting))}"
              f"\n     ảnh gốc vốn không có chữ → pull lại kèm --allow-source")
    print(f"  tiếp: python ims.py sheet {job.name} · python ims.py grid {job.name} → điền layout.json → python ims.py render {job.name}")


# ----------------------------- grid / render / sheet -----------------------------
def _keys(layout: dict, wanted: list[str]) -> list[str]:
    keys = list(layout["images"])
    if not wanted:
        return keys
    miss = [k for k in wanted if k not in layout["images"]]
    if miss:
        raise SystemExit(f"Không có ảnh {miss} trong layout — có: {keys}")
    return wanted


def cmd_grid(a):
    job = job_dir(a.job)
    _, layout = load(job)
    for key in _keys(layout, a.keys):
        base = job / layout["images"][key]["base"]
        if a.zoom:
            box = tuple(float(v) for v in a.zoom.split(","))
            if len(box) != 4 or not (0 <= box[0] < box[2] <= 100 and 0 <= box[1] < box[3] <= 100):
                raise SystemExit("--zoom cần x0,y0,x1,y1 theo % (vd --zoom 20,84,80,100)")
            print(f"[{key}] vùng {a.zoom} phóng to, vạch mỗi 2%: {tools.grid_zoom(base, job / 'qa' / f'{key}.zoom.jpg', box)}")
            continue
        is_cover = layout["images"][key].get("kind") == "cover"
        out, text = tools.grid(base, job / "qa" / f"{key}.grid.jpg", cover_frame_pct=13 if is_cover else 0)
        print(f"[{key}] {out}")
        print(text)
        if is_cover:
            print("  ẢNH BÌA: 13% đáy (y ≥ 87%) là vùng khung Shopee che — chữ + logo nằm phía trên; hook ở NỬA TRÊN ảnh.")


def cmd_render(a):
    from imslib.render import Studio
    job = job_dir(a.job)
    meta, layout = load(job)
    theme = kit.load(layout.get("shop") or meta["shop"])
    keys = [k for k in _keys(layout, a.keys) if a.keys or layout["images"][k].get("blocks")]
    skipped = [] if a.keys else [k for k in layout["images"] if k not in keys]
    n_err = n_warn = 0
    with Studio() as st:
        for key in keys:
            r = st.render(job, key, layout["images"][key], theme)
            errs = [i for i in r["issues"] if i["level"] == "LỖI"]
            warns = [i for i in r["issues"] if i["level"] == "CẢNH BÁO"]
            n_err += len(errs)
            n_warn += len(warns)
            mark = "✗" if errs else "⚠" if warns else "✓"
            print(f"{mark} [{key}] {KINDS.get(r['kind'], r['kind'])} {r['size'][0]}×{r['size'][1]} → {r['out']}"
                  + (f" · logo {r['logo']['file']}" if r["logo"] else "") + (f" · tông {r['tones']}" if r["tones"] else ""))
            for i in r["issues"]:
                print(f"    {i['level']:<8} {i['id']}: {i['msg']}")
            if r.get("tem"):
                print(f"    ảnh bìa như khách thấy (khung Shopee + cỡ tem): {job / r['tem']} — PHẢI nhìn ảnh này")
    if skipped:
        print(f"(bỏ qua {len(skipped)} ảnh chưa có khối nào: {', '.join(skipped)})")
    print(f"\n{'ĐẠT' if not n_err else 'CHƯA ĐẠT'} — {len(keys)} ảnh · {n_err} lỗi · {n_warn} cảnh báo · ảnh soát: {job / 'qa'}")
    if n_err:
        sys.exit(1)


def cmd_sheet(a):
    job = job_dir(a.job)
    meta, layout = load(job)
    for p in tools.sheet(job, meta, layout):
        print(p)


def cmd_board(a):
    job = job_dir(a.job)
    _, layout = load(job)
    out = tools.board(job, layout)
    if not out:
        raise SystemExit("Chưa có ảnh final nào — chạy `ims.py render` trước.")
    for p in out:
        print(p)


# ----------------------------- push -----------------------------
def cmd_push(a):
    job = job_dir(a.job)
    meta, layout = load(job)
    if not meta.get("listing_id"):
        raise SystemExit("Job này không gắn listing trên app (tạo bằng `new`) — không có gì để nộp.")
    todo = []
    for key in _keys(layout, a.keys):
        im, out, rep = meta["images"].get(key) or {}, job / "out" / f"{key}.jpg", job / "qa" / f"{key}.json"
        if not out.is_file() or not rep.is_file():
            if a.keys:
                raise SystemExit(f"[{key}] chưa render — chạy `ims.py render {a.job} {key}`")
            continue
        if out.stat().st_mtime < (job / "layout.json").stat().st_mtime - 1:
            raise SystemExit(f"[{key}] layout.json đã sửa SAU lần render cuối — render lại rồi mới nộp.")
        errs = [i for i in json.loads(rep.read_text(encoding="utf-8"))["issues"] if i["level"] == "LỖI"]
        if errs and not a.force:
            raise SystemExit(f"[{key}] QA còn {len(errs)} lỗi — sửa cho ĐẠT rồi nộp (hoặc --force nếu Sếp đã chấp nhận).")
        if not im.get("item_id"):
            raise SystemExit(f"[{key}] không có item_id trên app.")
        todo.append((key, im, out))
    if not todo:
        raise SystemExit("Không có ảnh nào đã render để nộp.")
    print(f"Sẽ GHI ĐÈ ảnh kết quả của {len(todo)} item trên listing {meta['listing_id']} ({meta['shop']}): "
          + ", ".join(k for k, _, _ in todo))
    if not a.yes:
        raise SystemExit("→ chưa nộp. Sếp duyệt ảnh rồi thì chạy lại kèm --yes.")
    kinds = set()
    for key, im, out in todo:
        app.upload_result(im["item_id"], out, a.note)
        im["pushed"] = out.stat().st_mtime
        kinds.add(im["kind"])
        print(f"  ✓ item {key} ← {out.name}")
    save(job / "job.json", meta)
    if a.review:
        for kind in sorted(kinds):
            if kind in ("cover", "product_image", "description_image"):
                app.request_review(meta["listing_id"], kind)
                print(f"  ✓ xin duyệt mục {KINDS[kind]}")
    print(f"✓ đã nộp {len(todo)} ảnh → {app.cfg()[0]}/marketing/listing/{meta['listing_id']}/work/")


def main():
    ap = argparse.ArgumentParser(description="GDP Image Studio", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("kit"); p.add_argument("action", choices=["sync", "show", "demo"]); p.add_argument("shop")
    p.add_argument("--listing", type=int); p.set_defaults(fn=cmd_kit)
    p = sub.add_parser("new"); p.add_argument("job"); p.add_argument("images", nargs="+"); p.add_argument("--shop", required=True)
    p.add_argument("--kind", default="product_image", choices=list(KINDS)); p.add_argument("--src", nargs="*"); p.add_argument("--name")
    p.set_defaults(fn=cmd_new)
    p = sub.add_parser("pull"); p.add_argument("listing_id", type=int); p.add_argument("--job"); p.add_argument("--kind", nargs="*", choices=list(KINDS))
    p.add_argument("--refresh", action="store_true", help="tải lại ảnh sạch dù đã có (ghi đè clean/)")
    p.add_argument("--allow-source", action="store_true", help="item chưa có ảnh sạch → dùng ảnh gốc làm nền (ảnh vốn không chữ)")
    p.add_argument("--sync-kit", action="store_true"); p.set_defaults(fn=cmd_pull)
    p = sub.add_parser("grid"); p.add_argument("job"); p.add_argument("keys", nargs="*")
    p.add_argument("--zoom", help="x0,y0,x1,y1 (%%): phóng to một vùng, vạch mỗi 2%% — đo ô icon / chi tiết nhỏ"); p.set_defaults(fn=cmd_grid)
    p = sub.add_parser("render"); p.add_argument("job"); p.add_argument("keys", nargs="*"); p.set_defaults(fn=cmd_render)
    p = sub.add_parser("sheet"); p.add_argument("job"); p.set_defaults(fn=cmd_sheet)
    p = sub.add_parser("board"); p.add_argument("job"); p.set_defaults(fn=cmd_board)
    p = sub.add_parser("push"); p.add_argument("job"); p.add_argument("keys", nargs="*"); p.add_argument("--yes", action="store_true")
    p.add_argument("--review", action="store_true"); p.add_argument("--force", action="store_true"); p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_push)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
