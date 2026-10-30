// Actual digit_01651 from backend/datasets/optical_digits_uci_v2.csv (label: 7).
// This sample has a clear top bar and diagonal, without the first sample's crossbar.
const PIXELS = [
  [0, 1, 10, 14, 16, 16, 15, 1],
  [0, 1, 12, 11, 8, 11, 15, 2],
  [0, 0, 0, 0, 1, 14, 8, 0],
  [0, 0, 0, 0, 11, 11, 1, 0],
  [0, 0, 0, 5, 16, 2, 0, 0],
  [0, 0, 1, 16, 6, 0, 0, 0],
  [0, 0, 7, 14, 1, 0, 0, 0],
  [0, 0, 15, 11, 0, 0, 0, 0],
];

export default function DigitMatrixExample() {
  return <figure className="digit-matrix-example">
    <div className="digit-matrix-layout">
    <div>
    <p className="digit-matrix-label">Pixel values</p>
    <table className="digit-pixel-matrix" aria-label="Eight by eight brightness matrix of a handwritten digit 7">
      <tbody>{PIXELS.map((row, rowIndex) => <tr key={rowIndex}>
        {row.map((value, columnIndex) => {
          const brightness = Math.round(value / 16 * 255);
          return <td key={columnIndex} style={{ backgroundColor: `rgb(${brightness}, ${brightness}, ${brightness})`, color: value >= 8 ? "#111" : "#fff" }}><span>{value}</span></td>;
        })}
      </tr>)}</tbody>
    </table>
    </div>
    <div>
      <p className="digit-matrix-label">The same values as an image</p>
      <svg className="digit-image-preview" viewBox="0 0 8 8" role="img" aria-label="A handwritten 7 with a horizontal top stroke and a diagonal down toward the left" shapeRendering="crispEdges">
        {PIXELS.flatMap((row, y) => row.map((value, x) => {
          const brightness = Math.round(value / 16 * 255);
          return <rect key={`${y}-${x}`} x={x} y={y} width={1} height={1} fill={`rgb(${brightness}, ${brightness}, ${brightness})`} />;
        }))}
      </svg>
    </div>
    </div>
    <figcaption>
      <strong>One real example labeled 7.</strong>
      Look for the top bar and the diagonal stroke. Each number is one pixel: 0 is black and 16 is white. Removing the numbers and grid lines reveals the same image the model receives.
    </figcaption>
  </figure>;
}
