from PIL import Image, ImageDraw

def create_icon(size, filename):
    # Colors
    PAPER = (255, 255, 255)
    INK = (0, 0, 0)
    
    # Create image
    img = Image.new('RGB', (size, size), color=PAPER)
    d = ImageDraw.Draw(img)
    
    # Draw Border (1px scaling? Make it proportional)
    border_width = max(1, size // 50)
    d.rectangle([0, 0, size-1, size-1], outline=INK, width=border_width)
    
    # Draw "V" - manual coordinates for a Serif-like V
    # 20% margin
    margin = size * 0.25
    bottom_y = size - margin
    top_y = margin
    
    # Center X
    center_x = size / 2
    
    # Points for a thick stroke V
    stroke = size * 0.08
    
    # Left Arm
    # Top Left
    p1 = (center_x - (size * 0.3), top_y)
    # Bottom Center
    p2 = (center_x, bottom_y)
    # Top Right
    p3 = (center_x + (size * 0.3), top_y)
    
    # Draw lines
    d.line([p1, p2], fill=INK, width=int(stroke))
    d.line([p2, p3], fill=INK, width=int(stroke))
    
    # Add a small decorative "Japanese seal" style red dot? 
    # No, strictly black and white per spec.
    
    img.save(f"icons/{filename}")
    print(f"Created {filename}")

if __name__ == "__main__":
    create_icon(192, "icon-192.png")
    create_icon(512, "icon-512.png")
