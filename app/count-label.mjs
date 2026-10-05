export function countLabel(count, singular) {
  return `${count.toLocaleString("en-US")} ${singular}${count === 1 ? "" : "s"}`;
}
