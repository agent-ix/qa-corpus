export function parse(text: string): number {
  return dangerousEval(text);
}

export function dangerousEval(text: string): number {
  return Number(text);
}
