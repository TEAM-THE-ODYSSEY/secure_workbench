from pid_engine.symbol_detector import SymbolDetector
from pid_engine.ocr import OCRAdapter
from pid_engine.line_detector import LineDetector
from pid_engine.pipeline import PIDPipeline
from pid_engine.preprocessing import load_image
from pid_engine.agents import PIDValidator


# -----------------------------------------
# 1. Load the real P&ID image
# -----------------------------------------

image_path = "sample_pid.png"

image = load_image(image_path)


# -----------------------------------------
# 2. Create P&ID processing components
# -----------------------------------------

symbol_detector = SymbolDetector(
    weights="../models/best.pt",
    conf=0.25
)

ocr = OCRAdapter()

line_detector = LineDetector()


# -----------------------------------------
# 3. Create the P&ID pipeline
# -----------------------------------------

pipeline = PIDPipeline(
    symbol_detector=symbol_detector,
    ocr=ocr,
    line_detector=line_detector
)


# -----------------------------------------
# 4. Analyze the P&ID
# -----------------------------------------

analysis = pipeline.analyze(image)


# -----------------------------------------
# 5. Display result
# -----------------------------------------

print("\n" + "=" * 70)
print("                    P&ID ANALYSIS")
print("=" * 70)

print("\nOBJECTS:")
for obj in analysis.objects:
    print(
        f"  {obj.object_id} | "
        f"type={obj.object_type} | "
        f"tag={obj.tag} | "
        f"confidence={obj.association_confidence:.3f}"
    )

print("\nLINES:")
for line in analysis.lines:
    print(
        f"  {line.line_id} | "
        f"type={line.line_type} | "
        f"confidence={line.confidence:.3f}"
    )

print("\nRELATIONSHIPS:")
for rel in analysis.relationships:
    print(
        f"  {rel.source} -> {rel.target} | "
        f"{rel.relationship} | "
        f"pipe={rel.pipe} | "
        f"confidence={rel.confidence:.3f}"
    )

print("\nWARNINGS:")
if analysis.warnings:
    for warning in analysis.warnings:
        print(f"  - {warning}")
else:
    print("  None")

print("\nVALIDATION:")
print(PIDValidator().validate(analysis))

print("\n" + "=" * 70)