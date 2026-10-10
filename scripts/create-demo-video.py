"""Build a narrated walkthrough from screenshots of the tested local app.
Requires macOS say and ffmpeg. No external accounts or services.
"""

import json, pathlib, subprocess, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILD = ROOT / ".build/video"
segments = [
    (
        "01-healthy",
        "Shopify seller: healthy baseline",
        "Meet Luma Goods, an independent seller running a Shopify website. They need to know whether a new release helps customers buy. ImpactGuard starts green. This local demo uses synthetic traffic and projects impact for one hundred and twenty checkout starts per day, at an eighty two dollar order value.",
    ),
    (
        "02-checkout",
        "Regression detected: red issue, $690/day exposure",
        "A payment redirect change now hurts checkout completion. The issue turns red. ImpactGuard estimates six hundred and ninety dollars a day in revenue exposure for this seller, if the pattern persists. This is a calculated scenario projection, not a claim about actual lost revenue.",
    ),
    (
        "03-investigation",
        "Affected segment: Safari and PayPal",
        "The investigation separates Safari and PayPal from other customers. Their completion rate drops from about seventy two percent to thirty eight percent. Other segments stay close to baseline. The engine shows sample counts, statistical evidence, and the exact dollar formula.",
    ),
    (
        "04-commit",
        "Suspect commit: payment redirect token handling",
        "The suspect commit changed PayPal token handling. ImpactGuard ranks it using timing, service files, and relevant diff terms. Developers can inspect the changed lines directly. The score identifies a plausible investigation candidate. It does not prove that the commit caused the problem.",
    ),
    (
        "05-recovery",
        "Remediation: measure fresh traffic, then turn green",
        "We simulate rolling back the faulty behavior. ImpactGuard generates six thousand fresh sessions and measures recovered checkout completion, near seventy two percent. The state turns green after measurement. No production rollback or external account action occurs.",
    ),
    (
        "06-margin",
        "Margin leak: stacked coupons cost $1,235/week",
        "The next change combines two coupon discounts. Orders can look healthy while profit disappears. ImpactGuard finds negative contribution margin and projects about twelve hundred and thirty five dollars a week of exposure for Luma Goods. The investigation points to the discount combiner.",
    ),
    (
        "07-retention",
        "Customer experience: delayed delivery and retention",
        "Delivery changes can also affect the seller. Mature synthetic customer cohorts show much lower repeat purchase rates after late deliveries. The annual number is an explicit scenario projection scaled to seller volume. Customer mix remains a possible explanation, so the finding stays an association.",
    ),
    (
        "08-bank",
        "Banking: 200 unsettled transfers posted as success",
        "The same approach extends to banking. A callback mapper marks failed and pending transfers as successful. ImpactGuard compares two thousand bank outcomes with application statuses and ledger postings. It finds two hundred mismatches and about forty seven thousand dollars in unbacked credits.",
    ),
    (
        "09-bank-diff",
        "Suspect commit: failed status falls through to success",
        "The diff exposes the mistake. Explicit checks for settled, failed, and pending statuses were replaced by a fallback that reports success. Application success is not evidence that cash arrived. Banking amounts use integer cents, and the reconciliation check evaluates ledger postings against settlement evidence.",
    ),
    (
        "10-bank-recovery",
        "Reconciliation: 200 reversals, zero remaining mismatches",
        "Remediation records two hundred corrective reversals and retains the original credits. The system verifies zero remaining mismatches and turns green. The project runs locally, with no Shopify, GitHub, bank, or cloud account connected. A real customer pilot would connect verified releases and business telemetry.",
    ),
]


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def stamp(seconds):
    millis = round(seconds * 1000)
    return f"{millis // 3600000:02}:{millis // 60000 % 60:02}:{millis // 1000 % 60:02},{millis % 1000:03}"


BUILD.mkdir(parents=True, exist_ok=True)
clips = []
srt = []
elapsed = 0
manifest = []
for index, (stem, title, narration) in enumerate(segments, 1):
    text = BUILD / f"{stem}.txt"
    text.write_text(narration)
    audio = BUILD / f"{stem}.aiff"
    run(["say", "-v", "Samantha", "-r", "175", "-f", str(text), "-o", str(audio)])
    duration = (
        float(
            subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(audio),
                ]
            )
        )
        + 1
    )
    caption = BUILD / f"{stem}-caption.txt"
    caption.write_text(f"{index:02d} / {title}")
    clip = BUILD / f"{stem}.mp4"
    filters = "scale=1728:1080,pad=1920:1080:96:0:color=0x18212e"
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-framerate",
            "24",
            "-i",
            str(ROOT / 'docs/demo-assets' / f"{stem}.png"),
            "-i",
            str(audio),
            "-vf",
            filters,
            "-af",
            "apad",
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(clip),
        ]
    )
    clips.append(clip)
    sentences = re.split(r"(?<=\.)\s+", narration)
    cursor = elapsed
    chars = sum(len(x) for x in sentences)
    for sentence in sentences:
        cue_duration = (duration - 1) * len(sentence) / chars
        srt.append(
            f"{len(srt) + 1}\n{stamp(cursor)} --> {stamp(cursor + cue_duration)}\n{sentence}\n"
        )
        cursor += cue_duration
    manifest.append({"chapter": title, "start": elapsed, "duration": duration})
    elapsed += duration
    print(f"Encoded {index}/{len(segments)}: {title}", flush=True)
concat = BUILD / "concat.txt"
concat.write_text("\n".join("file '" + str(p) + "'" for p in clips))
subtitles = ROOT / "output/ImpactGuard-demo.srt"
subtitles.write_text("\n".join(srt))
run(
    [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat),
        "-i",
        str(subtitles),
        "-map",
        "0:v",
        "-map",
        "0:a",
        "-map",
        "1:s",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=eng",
        "-movflags",
        "+faststart",
        str(ROOT / "output/ImpactGuard-demo.mp4"),
    ]
)
(ROOT / "output/video-chapters.json").write_text(json.dumps(manifest, indent=2))
print(f"Finished narrated video: {elapsed:.1f}s", flush=True)
