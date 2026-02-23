import express from 'express';
import cors from 'cors';
import { createClient } from '@supabase/supabase-js';

const app = express();
app.use(cors());
app.use(express.json());

const port = process.env.PORT || 8787;
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

const localState = {
  prompts: []
};

const supabase = supabaseUrl && supabaseServiceRoleKey
  ? createClient(supabaseUrl, supabaseServiceRoleKey)
  : null;

app.get('/api/health', (_, response) => {
  response.json({ ok: true, mode: supabase ? 'supabase' : 'local' });
});

app.get('/api/prompts', async (_, response) => {
  if (supabase) {
    const { data, error } = await supabase
      .from('prompts')
      .select('id,title,content,tags,model,versions:prompt_versions(version,created_at)')
      .order('created_at', { ascending: false });

    if (error) {
      response.status(500).json({ error: error.message });
      return;
    }

    response.json(data.map((row) => ({
      id: row.id,
      title: row.title,
      content: row.content,
      tags: row.tags ?? [],
      model: row.model,
      versions: (row.versions ?? []).map((version) => ({ version: version.version, createdAt: version.created_at }))
    })));
    return;
  }

  response.json(localState.prompts);
});

app.post('/api/prompts', async (request, response) => {
  const newPrompt = {
    id: crypto.randomUUID(),
    title: request.body.title,
    content: request.body.content,
    tags: request.body.tags ?? [],
    model: request.body.model,
    config: {
      temperature: request.body.temperature,
      top_p: request.body.top_p,
      max_tokens: request.body.max_tokens
    },
    examples: request.body.examples ?? [],
    versions: [{ version: 1, createdAt: new Date().toISOString(), content: request.body.content }],
    createdAt: new Date().toISOString()
  };

  if (supabase) {
    const { data, error } = await supabase
      .from('prompts')
      .insert({
        id: newPrompt.id,
        title: newPrompt.title,
        content: newPrompt.content,
        tags: newPrompt.tags,
        model: newPrompt.model,
        config: newPrompt.config,
        examples: newPrompt.examples
      })
      .select('id')
      .single();

    if (error) {
      response.status(500).json({ error: error.message });
      return;
    }

    const { error: versionsError } = await supabase
      .from('prompt_versions')
      .insert({ prompt_id: data.id, version: 1, content: newPrompt.content });

    if (versionsError) {
      response.status(500).json({ error: versionsError.message });
      return;
    }

    response.status(201).json({ id: data.id });
    return;
  }

  localState.prompts.unshift(newPrompt);
  response.status(201).json(newPrompt);
});

app.post('/api/ab-test', (request, response) => {
  const { promptA, promptB, modelA, modelB } = request.body;

  const seed = `${promptA}:${promptB}:${modelA}:${modelB}`;
  const score = Array.from(seed).reduce((total, char) => total + char.charCodeAt(0), 0);
  const winner = score % 2 === 0 ? `Prompt A (${modelA})` : `Prompt B (${modelB})`;

  response.json({ winner, rationale: 'Placeholder deterministic evaluator. Connect OpenAI eval later.' });
});

app.listen(port, () => {
  console.log(`PromptOps server running at http://localhost:${port}`);
});
