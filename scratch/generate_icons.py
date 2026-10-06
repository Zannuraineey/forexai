import os
from PIL import Image, ImageDraw, ImageFilter

def create_app_icon(size):
    # High-res master image (1024x1024)
    master_size = 1024
    img = Image.new("RGBA", (master_size, master_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background rounded rect
    margin = 40
    rect_box = [margin, margin, master_size - margin, master_size - margin]
    corner_radius = 210

    # Draw dark metallic slate background
    # Gradient simulation with concentric layers
    for r in range(corner_radius, 0, -10):
        pass
    draw.rounded_rectangle(rect_box, radius=corner_radius, fill=(15, 23, 42, 255)) # Slate 900

    # Inner subtle border
    draw.rounded_rectangle(rect_box, radius=corner_radius, outline=(30, 41, 59, 255), width=8)

    # Glowing subtle accent ring
    accent_box = [margin + 20, margin + 20, master_size - margin - 20, master_size - margin - 20]
    draw.rounded_rectangle(accent_box, radius=corner_radius - 20, outline=(16, 185, 129, 60), width=6)

    # 2. Candlestick 1 (Bearish or starting base, left)
    # Wick
    draw.line([(310, 360), (310, 720)], fill=(148, 163, 184, 255), width=18)
    # Body
    draw.rounded_rectangle([250, 440, 370, 640], radius=16, fill=(51, 65, 85, 255), outline=(100, 116, 139, 255), width=8)

    # 3. Candlestick 2 (Center continuation)
    # Wick
    draw.line([(512, 260), (512, 780)], fill=(52, 211, 153, 255), width=20)
    # Body (Emerald Bullish)
    draw.rounded_rectangle([440, 340, 584, 620], radius=20, fill=(16, 185, 129, 255), outline=(110, 231, 183, 255), width=10)

    # 4. Candlestick 3 (Right High Liquidity Expansion)
    # Wick
    draw.line([(714, 180), (714, 700)], fill=(251, 191, 36, 255), width=20)
    # Body (Gold / Amber Bullish Breakout)
    draw.rounded_rectangle([642, 240, 786, 500], radius=20, fill=(245, 158, 11, 255), outline=(253, 230, 138, 255), width=10)

    # 5. Upward Trend Impulse Wave Line
    trend_points = [(230, 680), (310, 540), (512, 420), (714, 260), (810, 180)]
    draw.line(trend_points, fill=(16, 185, 129, 200), width=16)

    # 6. AI Signal Core (Glowing diamond star at apex)
    apex_x, apex_y = 810, 180
    star_poly = [
        (apex_x, apex_y - 60),
        (apex_x + 18, apex_y - 18),
        (apex_x + 60, apex_y),
        (apex_x + 18, apex_y + 18),
        (apex_x, apex_y + 60),
        (apex_x - 18, apex_y + 18),
        (apex_x - 60, apex_y),
        (apex_x - 18, apex_y - 18),
    ]
    draw.polygon(star_poly, fill=(255, 255, 255, 255))

    # Resize to target density
    resized = img.resize((size, size), Image.Resampling.LANCZOS)
    return resized

def main():
    base_res = r"c:\Users\lenovo\.gemini\antigravity-ide\scratch\forex-ai-platform\frontend\android\app\src\main\res"
    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    for folder, dim in densities.items():
        out_dir = os.path.join(base_res, folder)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "ic_launcher.png")
        icon = create_app_icon(dim)
        icon.save(out_path, "PNG")
        print(f"Generated {out_path} ({dim}x{dim})")

if __name__ == "__main__":
    main()
