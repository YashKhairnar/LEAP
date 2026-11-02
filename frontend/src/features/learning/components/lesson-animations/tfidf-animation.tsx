"use client";

import LessonAnimation, { useStepPlayer } from "@/features/learning/components/lesson-animations/lesson-animation";

// Real values from the lesson pipeline: TF-IDF weights for "The mic is great." and how many
// of the 2,400 training reviews contain each word.
const WORDS = [
  { word: "great", weight: 0.41, reviews: 164 },
  { word: "is", weight: 0.28, reviews: 530 },
  { word: "mic", weight: 0.85, reviews: 2 },
  { word: "the", weight: 0.20, reviews: 1062 },
];
const SENTENCE = ["The", "mic", "is", "great."];

const CAPTIONS = [
  "Start with one review: \"The mic is great.\"",
  "TF-IDF gives every review a row with one column per vocabulary word, 4,558 here, in alphabetical order. Only this review's four words get a value; every other column is 0.",
  "Each word's value depends on how rare it is across reviews. 'mic' gets 0.85, while 'the' gets only 0.20.",
  "Here's why: 'the' appears in 1,062 of the 2,400 training reviews, so it says little about any one review. 'mic' appears in just 2.",
  "Rare words get high weights and common words get low ones. This row of 4,558 numbers is what the model sees instead of the text.",
];

export default function TfidfAnimation() {
  const player = useStepPlayer([1300, 2200, 2400, 2600]);
  const { step } = player;
  const slots: (typeof WORDS[number] | null)[] = [null, WORDS[0], null, WORDS[1], null, WORDS[2], null, WORDS[3], null];

  return <LessonAnimation
    title="Turn a review into numbers"
    summary="Animation: the words of 'The mic is great.' move into a row of 4,558 columns. Bars show their TF-IDF values: mic 0.85, great 0.41, is 0.28, the 0.20. Then a chart shows the is in 1,062 of 2,400 reviews and mic in 2."
    caption={CAPTIONS[step]}
    player={player}
  >
    <div className="tfidf-anim">
      <p className="tfidf-anim-sentence">
        {SENTENCE.map((word) => <span key={word} className={step >= 1 ? "is-sent" : ""}>{word}</span>)}
      </p>
      <div className={`tfidf-anim-row${step >= 1 ? " is-on" : ""}`}>
        {slots.map((slot, index) => slot
          ? <div key={index} className="tfidf-anim-slot is-word">
              <div className="tfidf-anim-bar"><span style={{ height: step >= 2 ? `${slot.weight * 100}%` : "0%" }} /></div>
              <strong>{step >= 2 ? slot.weight.toFixed(2) : "·"}</strong>
              <em>{slot.word}</em>
            </div>
          : <div key={index} className="tfidf-anim-slot is-zero"><strong>0 0 0</strong><em>…</em></div>)}
      </div>
      <p className="tfidf-anim-row-label">One row = one review · 4,558 columns · only 4 aren&apos;t 0</p>
      <div className={`tfidf-anim-rarity${step >= 3 ? " is-on" : ""}`}>
        <span className="tfidf-anim-rarity-title">Training reviews containing the word (of 2,400)</span>
        {[...WORDS].sort((a, b) => b.reviews - a.reviews).map((item) => <div key={item.word} className="tfidf-anim-rarity-row">
          <em>{item.word}</em>
          <div><span style={{ width: step >= 3 ? `${Math.max(0.6, (item.reviews / 1062) * 100)}%` : "0%" }} /></div>
          <strong>{item.reviews.toLocaleString("en-US")}</strong>
        </div>)}
      </div>
    </div>
  </LessonAnimation>;
}
