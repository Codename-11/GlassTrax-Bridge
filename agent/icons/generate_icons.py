"""
Generate tray icons for GlassTrax Agent

Run this script to create the .ico files:
    python generate_icons.py

Requires: Pillow (pip install Pillow)
"""

from pathlib import Path

from PIL import Image, ImageDraw


def create_icon(color: tuple, filename: str, size: int = 64) -> None:
    """Create an icon with a colored circle"""
    # Create RGBA image with transparent background
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw filled circle with white border
    margin = 4
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=color + (255,),
        outline=(255, 255, 255, 255),
        width=2,
    )

    # Save as ICO with multiple sizes
    output_path = Path(__file__).parent / filename

    # Create multiple sizes for ICO format
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
    imgs = []
    for s in sizes:
        resized = img.resize(s, Image.Resampling.LANCZOS)
        imgs.append(resized)

    # Save with all sizes
    imgs[0].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s, _ in sizes],
        append_images=imgs[1:],
    )
    print(f"Created: {output_path}")


def main():
    """Generate all icons"""
    icons = {
        "icon_running.ico": (34, 197, 94),  # Green #22c55e
        "icon_stopped.ico": (239, 68, 68),  # Red #ef4444
        "icon_error.ico": (234, 179, 8),  # Yellow #eab308
    }

    for filename, color in icons.items():
        create_icon(color, filename)

    print("\nAll icons generated successfully!")


if __name__ == "__main__":
    main()
