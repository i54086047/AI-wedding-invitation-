import os
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, url_for, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ====== 基本設定 ======
BASE_DIR = Path(__file__).resolve().parent
INVITES_DIR = BASE_DIR / "static" / "invites"
INVITES_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

def _ext_from_filename(filename: str) -> str:
    return Path(filename).suffix.lower()

def _validate_image(file_storage, field_name: str) -> str:
    if not file_storage or file_storage.filename == "":
        raise ValueError(f"缺少照片欄位：{field_name}")
    ext = _ext_from_filename(file_storage.filename)
    if ext not in ALLOWED_EXT:
        raise ValueError(f"{field_name} 圖片格式不支援：{ext}（只允許 jpg/jpeg/png/webp）")
    return ext

def _get_form_value(name: str, default: str = "", required: bool = False) -> str:
    v = (request.form.get(name) or "").strip()
    if required and not v:
        raise ValueError(f"缺少必填欄位：{name}")
    return v if v else default

@app.get("/")
def home():
    # 直接導到建立頁
    return render_template("create.html")

@app.get("/create")
def create_page():
    return render_template("create.html")

@app.post("/api/create")
def api_create():
    try:
        # ====== 1) 讀取文字欄位 ======
        data = {
            # page meta / topbar
            "page_title": _get_form_value("page_title", required=True),
            "brand_title": _get_form_value("brand_title", default="C & Y Wedding"),
            "brand_sub": _get_form_value("brand_sub", default="滑鼠滾輪一次切換一頁"),
            "rsvp_button_text": _get_form_value("rsvp_button_text", default="我要出席 RSVP"),

            # cover
            "couple_title": _get_form_value("couple_title", required=True),
            "cover_subtitle": _get_form_value("cover_subtitle", required=True),
            "wedding_date_text": _get_form_value("wedding_date_text", required=True),
            "wedding_time_text": _get_form_value("wedding_time_text", required=True),
            "venue_name": _get_form_value("venue_name", required=True),

            # story
            "story_title": _get_form_value("story_title", default="我們的故事"),
            "story_subtitle": _get_form_value("story_subtitle", required=True),
            "story_p1": _get_form_value("story_p1", required=True),
            "story_p2": _get_form_value("story_p2", required=True),

            # details
            "details_title": _get_form_value("details_title", default="Wedding Day"),
            "details_subtitle": _get_form_value("details_subtitle", default="當天流程與場地資訊"),
            "venue_address": _get_form_value("venue_address", required=True),
            "map_url": _get_form_value("map_url", required=True),
            "details_note": _get_form_value("details_note", default="＊若想內嵌 Google Map，我也可以幫你加 iframe。"),

            # timeline
            "tl1_time": _get_form_value("tl1_time", required=True),
            "tl1_text": _get_form_value("tl1_text", required=True),
            "tl2_time": _get_form_value("tl2_time", required=True),
            "tl2_text": _get_form_value("tl2_text", required=True),
            "tl3_time": _get_form_value("tl3_time", required=True),
            "tl3_text": _get_form_value("tl3_text", required=True),

            # rsvp
            "rsvp_title": _get_form_value("rsvp_title", default="RSVP 出席回覆"),
            "rsvp_subtitle": _get_form_value("rsvp_subtitle", default="為了讓我們能好好準備座位與餐點，請花一點時間填寫出席回覆。"),
            "rsvp_step1": _get_form_value("rsvp_step1", default="1) 點擊下方按鈕前往回覆表單（建議使用 Google 表單）。"),
            "rsvp_step2": _get_form_value("rsvp_step2", default="2) 填寫您的姓名、人數與飲食需求。"),
            "rsvp_step3": _get_form_value("rsvp_step3", default="3) 送出後，我們會在婚禮前再與您確認。"),
            "rsvp_url": _get_form_value("rsvp_url", required=True),
            "rsvp_hint": _get_form_value("rsvp_hint", default="＊若無法使用表單，也可以直接回覆這封電子喜帖的寄件人。"),

            # buttons
            "btn_view_details": _get_form_value("btn_view_details", default="查看婚禮資訊"),
            "btn_our_story": _get_form_value("btn_our_story", default="我們的故事"),
            "btn_next_details": _get_form_value("btn_next_details", default="下一頁：婚禮資訊"),
            "btn_back_cover": _get_form_value("btn_back_cover", default="回到封面"),
            "btn_open_map": _get_form_value("btn_open_map", default="在 Google 地圖中開啟"),
            "btn_next_rsvp": _get_form_value("btn_next_rsvp", default="下一頁：RSVP"),
            "btn_open_rsvp": _get_form_value("btn_open_rsvp", default="前往 RSVP 表單"),
            "btn_back_cover_2": _get_form_value("btn_back_cover_2", default="回到封面"),  # 如果你想在 rsvp 用不同文字可用
        }

        # ====== 2) 讀取照片檔（4張）並驗證格式 ======
        photo_cover = request.files.get("photo_cover")
        photo_story = request.files.get("photo_story")
        photo_details = request.files.get("photo_details")
        photo_rsvp = request.files.get("photo_rsvp")

        ext1 = _validate_image(photo_cover, "photo_cover")
        ext2 = _validate_image(photo_story, "photo_story")
        ext3 = _validate_image(photo_details, "photo_details")
        ext4 = _validate_image(photo_rsvp, "photo_rsvp")

        # ====== 3) 建立 invite 資料夾 ======
        invite_id = uuid.uuid4().hex[:10]   # 夠猜不到，也不會太長
        invite_dir = INVITES_DIR / invite_id
        photos_dir = invite_dir / "photos"
        invite_dir.mkdir(parents=True, exist_ok=True)
        photos_dir.mkdir(parents=True, exist_ok=True)

        # ====== 4) 存照片（固定檔名，方便模板）======
        # 你也可以硬轉 jpg，但 MVP 先照原副檔名存
        p1 = photos_dir / f"01-cover{ext1}"
        p2 = photos_dir / f"02-story{ext2}"
        p3 = photos_dir / f"03-details{ext3}"
        p4 = photos_dir / f"04-rsvp{ext4}"

        photo_cover.save(p1)
        photo_story.save(p2)
        photo_details.save(p3)
        photo_rsvp.save(p4)

        # ====== 5) 準備模板要用的圖片 URL（相對於 /static）======
        data["photo_cover"] = f"/static/invites/{invite_id}/photos/{p1.name}"
        data["photo_story"] = f"/static/invites/{invite_id}/photos/{p2.name}"
        data["photo_details"] = f"/static/invites/{invite_id}/photos/{p3.name}"
        data["photo_rsvp"] = f"/static/invites/{invite_id}/photos/{p4.name}"

        # ====== 6) render 成 HTML，寫到 static 檔案 ======
        html = render_template("template_zh.html", **data)
        (invite_dir / "index.html").write_text(html, encoding="utf-8")

        # ====== 7) 回傳可分享 URL ======
        invite_url = f"/static/invites/{invite_id}/index.html"
        # 也可以做短一點的路由（見下方 /invites/<id>/）
        short_url = url_for("view_invite", invite_id=invite_id)

        return jsonify({
            "ok": True,
            "invite_id": invite_id,
            "url": short_url,
            "direct_static_url": invite_url
        })

    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except Exception as e:
        # 真的上線會改更安全的錯誤處理
        return jsonify({"ok": False, "error": f"Server error: {e}"}), 500


@app.get("/invites/<invite_id>/")
def view_invite(invite_id: str):
    # 給一個比較好看的短網址：/invites/<id>/
    # 實際內容仍是 static 內的 index.html
    p = INVITES_DIR / invite_id / "index.html"
    if not p.exists():
        abort(404)
    # 直接回傳靜態檔
    # Flask 內建 static 的 serve 不會自動 serve 這裡，所以用 send_file 最簡單
    from flask import send_file
    return send_file(p, mimetype="text/html; charset=utf-8")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
