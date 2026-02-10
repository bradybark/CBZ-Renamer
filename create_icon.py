from PIL import Image, ImageDraw

def create_manga_icon():
    # Render at high resolution with supersampling for max sharpness
    ss = 4  # 4x supersampling
    canvas_size = 256 * ss  # 1024x1024 working canvas
    size = (canvas_size, canvas_size)

    # Colors
    bg_color = "#000000"  # Pure Black
    fg_color = "#FFFFFF"  # White
    fg_color = "#FFFFFF"  # White

    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Background: Solid Black Rounded Square
    margin = 16 * ss
    draw.rounded_rectangle(
        [margin, margin, size[0]-margin, size[1]-margin],
        radius=40 * ss,
        fill=bg_color,
        outline=None
    )

    # 2. Icon: "Comic/Manga Page" Symbol — a rectangle with panel dividers
    pw = 140 * ss
    ph = 180 * ss
    cx, cy = size[0]//2, size[1]//2
    x1, y1 = cx - pw//2, cy - ph//2
    x2, y2 = cx + pw//2, cy + ph//2

    # Draw Page Outline (White, thick stroke)
    stroke = 10 * ss
    draw.rectangle([x1, y1, x2, y2], outline=fg_color, width=stroke)

    # Draw Panel Dividers (White)
    div_y = y1 + ph//3
    draw.line([x1, div_y, x2, div_y], fill=fg_color, width=stroke)

    div_x = cx + 20 * ss  # slightly off-center
    draw.line([div_x, div_y, div_x, y2], fill=fg_color, width=stroke)

    # --- Save PNG at 256x256 (for wm_iconphoto — sharp taskbar/header) ---
    img_256 = img.resize((256, 256), Image.Resampling.LANCZOS)
    img_256.save("app_icon.png", format='PNG')
    print("Saved app_icon.png (256x256)")

    # --- Save ICO with individually rendered sizes (for .exe embedding) ---
    ico_sizes = [256, 128, 64, 48, 32, 16]
    ico_images = []
    for s in ico_sizes:
        resized = img.resize((s, s), Image.Resampling.LANCZOS)
        ico_images.append(resized)

    # Save first image with appended frames for multi-size ICO
    ico_images[0].save(
        "app_icon.ico", format='ICO',
        append_images=ico_images[1:],
        sizes=[(s, s) for s in ico_sizes]
    )
    print(f"Saved app_icon.ico (sizes: {ico_sizes})")

if __name__ == "__main__":
    create_manga_icon()
