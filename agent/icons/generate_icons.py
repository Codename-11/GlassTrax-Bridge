"""
Generate tray icons for GlassTrax Agent

Creates icons matching the GlassTrax Bridge branding with the "bridge" design.
Different states are indicated by the center bridge color.

Run this script to create the .ico files:
    python generate_icons.py

Requires: Pillow (pip install Pillow)
"""

from pathlib import Path

from PIL import Image, ImageDraw


def create_bridge_icon(center_color: tuple, filename: str, size: int = 64) -> None:
    """
    Create an icon with the GlassTrax bridge design.

    The design matches favicon.svg:
    - Dark background with rounded corners
    - White horizontal bars (top and bottom)
    - Three bridge segments with colored center
    """
    # Create RGBA image
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Colors
    bg_color = (30, 30, 30, 255)  # #1e1e1e
    white = (255, 255, 255, 255)

    # Scale factor (design is based on 32x32)
    scale = size / 32

    # Background with rounded corners
    radius = int(4 * scale)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=bg_color)

    # Helper to scale coordinates
    def s(val):
        return int(val * scale)

    # Top bars
    draw.rectangle([s(4), s(6), s(14), s(9)], fill=white)
    draw.rectangle([s(18), s(6), s(28), s(9)], fill=white)

    # Bridge segments (3 parts)
    # Left segment - white
    draw.rectangle([s(4), s(14), s(9), s(18)], fill=white)
    # Center segment - colored (status indicator)
    draw.rectangle([s(13), s(14), s(19), s(18)], fill=center_color + (255,))
    # Right segment - white
    draw.rectangle([s(23), s(14), s(28), s(18)], fill=white)

    # Bottom bars
    draw.rectangle([s(4), s(23), s(15), s(26)], fill=white)
    draw.rectangle([s(17), s(23), s(28), s(26)], fill=white)

    # Save as ICO with multiple sizes
    output_path = Path(__file__).parent / filename

    # Create multiple sizes for ICO format
    # Include 256x256 for Windows Explorer and Inno Setup
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    imgs = []
    for s_size in sizes:
        if s_size[0] == size:
            imgs.append(img.copy())
        else:
            # Recreate at each size for better quality
            resized_img = Image.new("RGBA", s_size, (0, 0, 0, 0))
            resized_draw = ImageDraw.Draw(resized_img)
            rs = s_size[0] / 32  # scale factor

            # Background
            r = int(4 * rs)
            resized_draw.rounded_rectangle(
                [0, 0, s_size[0] - 1, s_size[1] - 1],
                radius=r,
                fill=bg_color
            )

            def rs_scale(val):
                return int(val * rs)

            # Top bars
            resized_draw.rectangle([rs_scale(4), rs_scale(6), rs_scale(14), rs_scale(9)], fill=white)
            resized_draw.rectangle([rs_scale(18), rs_scale(6), rs_scale(28), rs_scale(9)], fill=white)

            # Bridge segments
            resized_draw.rectangle([rs_scale(4), rs_scale(14), rs_scale(9), rs_scale(18)], fill=white)
            resized_draw.rectangle([rs_scale(13), rs_scale(14), rs_scale(19), rs_scale(18)], fill=center_color + (255,))
            resized_draw.rectangle([rs_scale(23), rs_scale(14), rs_scale(28), rs_scale(18)], fill=white)

            # Bottom bars
            resized_draw.rectangle([rs_scale(4), rs_scale(23), rs_scale(15), rs_scale(26)], fill=white)
            resized_draw.rectangle([rs_scale(17), rs_scale(23), rs_scale(28), rs_scale(26)], fill=white)

            imgs.append(resized_img)

    # Save with all sizes
    imgs[-1].save(
        output_path,
        format="ICO",
        sizes=[s for s in sizes],
        append_images=imgs[:-1],
    )
    print(f"Created: {output_path}")


def main():
    """Generate all icons with bridge design"""
    icons = {
        "icon_running.ico": (74, 222, 128),   # Green #4ade80 (matches brand)
        "icon_stopped.ico": (239, 68, 68),    # Red #ef4444
        "icon_error.ico": (234, 179, 8),      # Yellow #eab308
    }

    for filename, color in icons.items():
        create_bridge_icon(color, filename)

    print("\nAll icons generated successfully!")
    print("Icons use the GlassTrax Bridge branding with colored center segment.")


if __name__ == "__main__":
    main()
