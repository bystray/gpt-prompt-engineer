interface Weights {
  quality: number;
  latency: number;
  cost: number;
  context: number;
  multimodal: number;
}

const models = [
  { id: 'gpt-4o', quality: 5, latency: 3, cost: 2, context: 5, multimodal: 5 },
  { id: 'gpt-4o-mini', quality: 4, latency: 5, cost: 5, context: 4, multimodal: 4 },
  { id: 'o3-mini', quality: 4, latency: 4, cost: 4, context: 3, multimodal: 3 }
];

Deno.serve(async (request) => {
  const weights = (await request.json()) as Weights;

  const ranked = models
    .map((model) => ({
      model: model.id,
      score:
        weights.quality * model.quality +
        weights.latency * model.latency +
        weights.cost * model.cost +
        weights.context * model.context +
        weights.multimodal * model.multimodal
    }))
    .sort((a, b) => b.score - a.score);

  return new Response(JSON.stringify({ recommendation: ranked[0], ranked }), {
    headers: { 'Content-Type': 'application/json' }
  });
});
