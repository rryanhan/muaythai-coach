import styles from "./wireframes.module.css";

type CalibrationKind =
  | "setup"
  | "visibility"
  | "locked"
  | "guard"
  | "lead"
  | "rear"
  | "movement"
  | "round";

type LandscapeFrameData = {
  caption: string;
  cue: string;
  kind: CalibrationKind;
  stage: string;
  status: string;
  step?: number;
};

const calibrationSteps = ["Frame", "Guard", "Lead", "Rear", "Move"];

const landscapeFrames: LandscapeFrameData[] = [
  {
    caption: "Setup / Turn phone sideways",
    cue: "Turn phone sideways",
    kind: "setup",
    stage: "Before camera",
    status: "Place phone"
  },
  {
    caption: "Full Body Visibility Check",
    cue: "Step back",
    kind: "visibility",
    stage: "Calibration",
    status: "Scanning",
    step: 0
  },
  {
    caption: "Full Body Locked",
    cue: "Hold still",
    kind: "locked",
    stage: "Calibration",
    status: "Locked",
    step: 0
  },
  {
    caption: "Fight Stance Guard",
    cue: "Guard stance",
    kind: "guard",
    stage: "Calibration",
    status: "Checking",
    step: 1
  },
  {
    caption: "Lead Reach",
    cue: "Extend lead hand",
    kind: "lead",
    stage: "Calibration",
    status: "Reach",
    step: 2
  },
  {
    caption: "Rear Reach",
    cue: "Extend rear hand",
    kind: "rear",
    stage: "Calibration",
    status: "Reach",
    step: 3
  },
  {
    caption: "Movement Baseline",
    cue: "Move left",
    kind: "movement",
    stage: "Calibration",
    status: "Baseline",
    step: 4
  },
  {
    caption: "Active 60-second Round",
    cue: "Shadowbox",
    kind: "round",
    stage: "60s round",
    status: "0:42"
  }
];

const patternCards = [
  {
    title: "Jab heavy",
    detail: "Vary entries with cross or angle."
  },
  {
    title: "Cross short",
    detail: "Rear hand stopped short."
  },
  {
    title: "Feet crossed",
    detail: "Reset stance after side steps."
  }
];

const feedbackClips = ["Feet crossing", "Short cross", "Jab repeat"];

export default function WireframesPage() {
  return (
    <main className={styles.board}>
      <header className={styles.boardHeader}>
        <p>Living Wireframe Board</p>
        <h1>Shadowboxing Coach MVP</h1>
      </header>

      <section className={styles.landscapeGrid} aria-label="Landscape calibration frames">
        {landscapeFrames.map((frame) => (
          <article className={styles.frameCard} key={frame.caption}>
            <div className={styles.frameCaption}>
              <span>{frame.caption}</span>
              <strong>{frame.stage}</strong>
            </div>
            <LandscapeFrame data={frame} />
          </article>
        ))}
      </section>

      <section className={styles.reviewSection} aria-label="Portrait review frame">
        <article className={styles.frameCard}>
          <div className={styles.frameCaption}>
            <span>Round Review</span>
            <strong>Portrait feedback</strong>
          </div>
          <PortraitReviewFrame />
        </article>
      </section>
    </main>
  );
}

function LandscapeFrame({ data }: { data: LandscapeFrameData }) {
  const isSetup = data.kind === "setup";
  return (
    <div className={`${styles.landscapeFrame} ${styles[`kind_${data.kind}`]}`}>
      <CameraTexture />

      {isSetup ? (
        <SetupVisual />
      ) : (
        <>
          <CalibrationProgress activeStep={data.step ?? 0} />
          <GuideOverlay kind={data.kind} />
        </>
      )}

      <div className={styles.heroPrompt}>
        <h2>{data.cue}</h2>
      </div>

      {data.kind === "round" ? (
        <div className={styles.roundHud}>
          <strong>0:42</strong>
          <span>Stay in frame</span>
        </div>
      ) : null}
    </div>
  );
}

function CameraTexture() {
  return (
    <>
      <div className={styles.cameraGradient} />
      <div className={styles.cameraGrid} />
    </>
  );
}

function CalibrationProgress({ activeStep }: { activeStep: number }) {
  return (
    <div className={styles.calibrationProgress}>
      {calibrationSteps.map((step, index) => (
        <div className={styles.progressItem} data-state={progressState(index, activeStep)} key={step}>
          <span>{step}</span>
          <i />
        </div>
      ))}
    </div>
  );
}

function progressState(index: number, activeStep: number) {
  if (index < activeStep) return "done";
  if (index === activeStep) return "active";
  return "idle";
}

function SetupVisual() {
  return (
    <div className={styles.setupVisual}>
      <div className={styles.phoneLandscape}>
        <div />
      </div>
      <div className={styles.tripodLine} />
      <div className={styles.floorLine} />
    </div>
  );
}

function GuideOverlay({ kind }: { kind: CalibrationKind }) {
  return (
    <div className={styles.guideLayer}>
      <svg aria-hidden="true" className={styles.poseSvg} viewBox="0 0 760 428">
        <defs>
          <linearGradient id={`ghost-${kind}`} x1="0" x2="1" y1="0" y2="1">
            <stop offset="0%" stopColor="#f4f5f0" stopOpacity="0.95" />
            <stop offset="100%" stopColor="#cfd7d1" stopOpacity="0.72" />
          </linearGradient>
          <filter id={`soft-${kind}`}>
            <feDropShadow dx="0" dy="14" floodColor="#000000" floodOpacity="0.18" stdDeviation="10" />
          </filter>
        </defs>

        {kind === "visibility" || kind === "locked" ? (
          <rect
            className={styles.bodyTarget}
            data-good={kind === "locked"}
            height="298"
            rx="124"
            width="188"
            x="286"
            y="70"
          />
        ) : null}

        {kind === "movement" ? (
          <MovementArrows />
        ) : null}

        {(kind === "lead" || kind === "rear") ? <ReachTarget side={kind} /> : null}

        <GhostFigure kind={kind} />
        <TrackedSkeleton kind={kind} />
      </svg>

      {kind !== "round" ? (
        <div className={styles.alignmentChips}>
          {alignmentLabels(kind).map((label) => (
            <span data-good={kind === "locked"} key={label}>
              {label}
            </span>
          ))}
        </div>
      ) : null}

      {kind === "locked" ? (
        <div className={styles.lockProgress}>
          <span />
        </div>
      ) : null}
    </div>
  );
}

function alignmentLabels(kind: CalibrationKind) {
  switch (kind) {
    case "visibility":
      return ["Feet in frame", "Hands visible"];
    case "locked":
      return ["Full body visible"];
    case "guard":
      return ["Guard up"];
    case "lead":
      return ["Lead hand"];
    case "rear":
      return ["Rear hand"];
    case "movement":
      return ["Move right"];
    default:
      return ["Hands visible"];
  }
}

function GhostFigure({ kind }: { kind: CalibrationKind }) {
  const leadReach = kind === "lead";
  const rearReach = kind === "rear";
  return (
    <g className={styles.ghostFigure} filter={`url(#soft-${kind})`}>
      <ellipse cx="380" cy="86" rx="23" ry="28" />
      <rect height="24" rx="12" width="18" x="371" y="112" />
      <rect height="118" rx="42" width="88" x="336" y="132" />
      <rect height="52" rx="24" width="106" x="327" y="238" />

      <line x1="338" x2={leadReach ? "228" : "302"} y1="158" y2={leadReach ? "148" : "214"} />
      <line x1={leadReach ? "228" : "302"} x2={leadReach ? "176" : "342"} y1={leadReach ? "148" : "214"} y2={leadReach ? "148" : "238"} />

      <line x1="422" x2={rearReach ? "548" : "462"} y1="158" y2={rearReach ? "150" : "214"} />
      <line x1={rearReach ? "548" : "462"} x2={rearReach ? "604" : "420"} y1={rearReach ? "150" : "214"} y2={rearReach ? "150" : "238"} />

      <line x1="348" x2="306" y1="278" y2="372" />
      <line x1="412" x2="462" y1="278" y2="372" />
      <ellipse cx="294" cy="376" rx="34" ry="11" />
      <ellipse cx="474" cy="376" rx="34" ry="11" />
    </g>
  );
}

function TrackedSkeleton({ kind }: { kind: CalibrationKind }) {
  const good = kind === "locked";
  const leadReach = kind === "lead";
  const rearReach = kind === "rear";
  return (
    <g className={styles.trackedSkeleton} data-good={good}>
      <circle cx="382" cy="94" r="16" />
      <line x1="382" x2="382" y1="114" y2="238" />
      <line x1="332" x2="432" y1="150" y2="150" />
      <line x1="332" x2={leadReach ? "220" : "294"} y1="150" y2={leadReach ? "150" : "206"} />
      <line x1={leadReach ? "220" : "294"} x2={leadReach ? "168" : "334"} y1={leadReach ? "150" : "206"} y2={leadReach ? "150" : "232"} />
      <line x1="432" x2={rearReach ? "554" : "468"} y1="150" y2={rearReach ? "150" : "206"} />
      <line x1={rearReach ? "554" : "468"} x2={rearReach ? "612" : "422"} y1={rearReach ? "150" : "206"} y2={rearReach ? "150" : "232"} />
      <line x1="338" x2="426" y1="252" y2="252" />
      <line x1="338" x2="308" y1="252" y2="370" />
      <line x1="426" x2="462" y1="252" y2="370" />
      {[
        [382, 94],
        [332, 150],
        [432, 150],
        [leadReach ? 168 : 334, leadReach ? 150 : 232],
        [rearReach ? 612 : 422, rearReach ? 150 : 232],
        [338, 252],
        [426, 252],
        [308, 370],
        [462, 370]
      ].map(([cx, cy], index) => (
        <circle cx={cx} cy={cy} key={`${cx}-${cy}-${index}`} r="6" />
      ))}
    </g>
  );
}

function ReachTarget({ side }: { side: "lead" | "rear" }) {
  const x = side === "lead" ? 150 : 610;
  return (
    <g className={styles.reachTarget}>
      <circle cx={x} cy="150" r="24" />
      <path d={side === "lead" ? "M190 150H238" : "M570 150H522"} />
    </g>
  );
}

function MovementArrows() {
  return (
    <g className={styles.movementArrows}>
      <path d="M380 286h-96" />
      <path d="M284 286l22-18" />
      <path d="M284 286l22 18" />
      <path d="M380 286h96" />
      <path d="M476 286l-22-18" />
      <path d="M476 286l-22 18" />
      <path d="M380 286v-70" />
      <path d="M380 216l-18 22" />
      <path d="M380 216l18 22" />
      <path d="M380 286v70" />
      <path d="M380 356l-18-22" />
      <path d="M380 356l18-22" />
    </g>
  );
}

function PortraitReviewFrame() {
  return (
    <div className={styles.portraitFrame}>
      <div className={styles.reviewHero}>
        <span>Round review</span>
        <h2>60 seconds analyzed</h2>
      </div>

      <div className={styles.reviewBlock}>
        <div className={styles.blockHeader}>
          <strong>Strike distribution</strong>
          <span>This round</span>
        </div>
        <StrikeDistribution />
      </div>

      <div className={styles.reviewBlock}>
        <div className={styles.blockHeader}>
          <strong>Movement map</strong>
          <span>Direction</span>
        </div>
        <MovementMap />
      </div>

      <div className={styles.patternGrid}>
        {patternCards.map((card) => (
          <article className={styles.patternCard} key={card.title}>
            <strong>{card.title}</strong>
            <span>{card.detail}</span>
          </article>
        ))}
      </div>

      <FeedbackClips />
    </div>
  );
}

function StrikeDistribution() {
  const strikes = [
    ["Jab", 44],
    ["Cross", 25],
    ["Hook", 18],
    ["Kick", 13]
  ] as const;

  return (
    <div className={styles.strikeDistribution}>
      <div className={styles.strikeWeb}>
        {strikes.map(([label, value], index) => (
          <span
            className={styles.webPoint}
            data-index={index}
            key={label}
            style={{ "--size": `${value + 34}px` } as React.CSSProperties}
          >
            {label}
          </span>
        ))}
      </div>
      <div className={styles.strikeList}>
        {strikes.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}%</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function MovementMap() {
  const moves = [
    ["Back", "12"],
    ["Left", "18"],
    ["Center", "31"],
    ["Right", "15"],
    ["Forward", "24"]
  ];
  return (
    <div className={styles.movementMap}>
      {moves.map(([label, value]) => (
        <div className={styles.moveCell} key={label}>
          <strong>{value}%</strong>
          <span>{label}</span>
        </div>
      ))}
    </div>
  );
}

function FeedbackClips() {
  return (
    <div className={styles.feedbackClips}>
      <div className={styles.blockHeader}>
        <strong>Feedback clips</strong>
        <span>3 clips</span>
      </div>
      <div className={styles.clipRow}>
        {feedbackClips.map((clip) => (
          <article className={styles.clipCard} key={clip}>
            <div />
            <strong>{clip}</strong>
          </article>
        ))}
      </div>
    </div>
  );
}
