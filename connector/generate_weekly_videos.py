"""Create honest, branded weekly MP4s from authenticated server analytics."""
from datetime import datetime, timezone
from getpass import getpass
import json
import os
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
import requests


API = os.getenv("BETHEL_API_URL", "https://bethel-api.onrender.com").rstrip("/")
OUTPUT = Path(os.getenv("BETHEL_MEDIA_OUTPUT", "weekly-media"))
FPS, SECONDS = 24, 7
FORMATS = {"vertical": (1080, 1920), "square": (1080, 1080), "landscape": (1920, 1080)}
NAVY, BLUE, CYAN, WHITE, MUTED = "#06152e", "#155eef", "#14b8d4", "#ffffff", "#b7c7e6"


def font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def get_admin_token():
    token = os.getenv("BETHEL_ADMIN_TOKEN", "").strip()
    if token:
        return token

    print("Sign in to Bethel to create the protected weekly report.")
    identifier = input("Admin email or mobile number: ").strip()
    password = getpass("Admin password (hidden): ")
    response = requests.post(
        API + "/auth/login",
        json={"identifier": identifier, "password": password},
        timeout=30,
    )
    password = ""
    if not response.ok:
        try:
            detail = response.json().get("detail", "Login failed")
        except ValueError:
            detail = "Login failed"
        raise RuntimeError(detail)
    result = response.json()
    if result.get("user", {}).get("role") not in {"admin", "super_admin"}:
        raise RuntimeError("This account does not have admin access")
    token = result.get("access_token", "")
    if not token:
        raise RuntimeError("The server did not return an access token")
    return token


def get_report():
    token = get_admin_token()
    response = requests.get(API + "/media/weekly-report", headers={"Authorization": f"Bearer {token}"}, timeout=30)
    response.raise_for_status()
    report = response.json()
    if report.get("status") != "verified":
        raise RuntimeError("Not enough verified snapshots to create a weekly report")
    return report


def centered(draw, text, y, width, face, fill=WHITE):
    box = draw.textbbox((0, 0), text, font=face)
    draw.text(((width - (box[2] - box[0])) / 2, y), text, font=face, fill=fill)


def frame(report, size, progress):
    width, height = size
    image = Image.new("RGB", size, NAVY)
    draw = ImageDraw.Draw(image)
    draw.ellipse((int(width*.55), -int(width*.3), int(width*1.25), int(width*.4)), fill="#0b3470")
    draw.rounded_rectangle((int(width*.08), int(height*.16), int(width*.92), int(height*.82)), radius=40, fill="#0b2144", outline=BLUE, width=4)
    mode = report["account_mode"]
    centered(draw, "BETHEL", int(height*.045), width, font(max(36, int(width*.055)), True), CYAN)
    centered(draw, f"VERIFIED {mode} WEEKLY REPORT", int(height*.105), width, font(max(22, int(width*.026)), True), MUTED)
    pnl = float(report["weekly_pnl"])
    label = "WEEKLY PROFIT" if pnl > 0 else "WEEKLY RESULT"
    centered(draw, label, int(height*.23), width, font(max(25, int(width*.032)), True), MUTED)
    amount = f"{'+' if pnl > 0 else ''}{pnl:,.2f}"
    amount_color = "#3ee6a8" if pnl > 0 else "#ff8b8b"
    centered(draw, amount, int(height*.29), width, font(max(58, int(width*.092)), True), amount_color)
    centered(draw, f"Return  {report['weekly_return_percent']:+.2f}%", int(height*.41), width, font(max(30, int(width*.045)), True))
    metrics = [
        f"Closed trades   {report['closed_trades']}",
        f"Win rate        {report['win_rate_percent']:.2f}%",
        f"Max drawdown    {report['maximum_drawdown_percent']:.2f}%",
    ]
    for index, text in enumerate(metrics):
        centered(draw, text, int(height*(.50 + index*.065)), width, font(max(23, int(width*.03))), MUTED)
    bar_x1, bar_x2, bar_y = int(width*.16), int(width*.84), int(height*.73)
    draw.rounded_rectangle((bar_x1, bar_y, bar_x2, bar_y+14), radius=7, fill="#16335f")
    draw.rounded_rectangle((bar_x1, bar_y, bar_x1+int((bar_x2-bar_x1)*progress), bar_y+14), radius=7, fill=CYAN)
    disclosure = f"{mode} account • Past performance does not guarantee future results."
    centered(draw, disclosure, int(height*.87), width, font(max(16, int(width*.018))), MUTED)
    centered(draw, "betheltradingtechnologies.com", int(height*.92), width, font(max(18, int(width*.022)), True), WHITE)
    return image


def write_video(report, name, size):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"bethel-weekly-{name}-{datetime.now(timezone.utc):%Y-%m-%d}.mp4"
    writer = imageio_ffmpeg.write_frames(
        str(path), size, fps=FPS, codec="libx264", pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p", macro_block_size=1,
        output_params=["-movflags", "+faststart", "-crf", "20"],
    )
    writer.send(None)
    try:
        total = FPS * SECONDS
        for index in range(total):
            writer.send(frame(report, size, index/(total-1)).tobytes())
    finally:
        writer.close()
    return path


if __name__ == "__main__":
    data = get_report()
    print(json.dumps(data, indent=2))
    for format_name, dimensions in FORMATS.items():
        print("Created", write_video(data, format_name, dimensions))
