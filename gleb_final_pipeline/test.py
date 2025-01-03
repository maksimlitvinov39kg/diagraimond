from PIL import Image, ImageDraw, ImageFont

image = Image.new('RGB', (512, 100), color='white')

draw = ImageDraw.Draw(image)
try:
    font = ImageFont.truetype("arial.ttf", 30)
except IOError:
    font = ImageFont.load_default(22)

text = "ZDES' DOLZHNA BIT DIAGRAMMA (SLON)"
draw.text((10, 30), text, fill="black", font=font)

image.save("output.png")

