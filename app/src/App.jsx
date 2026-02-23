import React, { useEffect, useMemo, useState } from 'react';

const emptyPrompt = {
  title: '',
  content: '',
  tags: '',
  model: 'gpt-4o-mini',
  temperature: 0.7,
  top_p: 1,
  max_tokens: 800,
  examples: '',
  qualityScore: 3
};

const modelProfiles = [
  { id: 'gpt-4o', quality: 5, latency: 3, cost: 2, context: 5, multimodal: 5 },
  { id: 'gpt-4o-mini', quality: 4, latency: 5, cost: 5, context: 4, multimodal: 4 },
  { id: 'o3-mini', quality: 4, latency: 4, cost: 4, context: 3, multimodal: 3 }
];

function scoreModel(taskWeights, model) {
  return (
    taskWeights.quality * model.quality +
    taskWeights.latency * model.latency +
    taskWeights.cost * model.cost +
    taskWeights.context * model.context +
    taskWeights.multimodal * model.multimodal
  );
}

export default function App() {
  const [prompt, setPrompt] = useState(emptyPrompt);
  const [prompts, setPrompts] = useState([]);
  const [selectedPromptId, setSelectedPromptId] = useState(null);
  const [taskWeights, setTaskWeights] = useState({ quality: 5, latency: 3, cost: 3, context: 4, multimodal: 2 });
  const [abTest, setAbTest] = useState({ promptA: '', promptB: '', modelA: 'gpt-4o', modelB: 'gpt-4o-mini' });

  const selectedPrompt = useMemo(() => prompts.find((item) => item.id === selectedPromptId), [prompts, selectedPromptId]);

  useEffect(() => {
    loadPrompts();
  }, []);

  async function loadPrompts() {
    const response = await fetch('http://localhost:8787/api/prompts');
    const data = await response.json();
    setPrompts(data);
  }

  async function savePrompt(event) {
    event.preventDefault();

    await fetch('http://localhost:8787/api/prompts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...prompt,
        tags: prompt.tags.split(',').map((tag) => tag.trim()).filter(Boolean),
        examples: prompt.examples.split('\n').filter(Boolean)
      })
    });

    setPrompt(emptyPrompt);
    await loadPrompts();
  }

  const recommendation = useMemo(() => {
    const ranked = modelProfiles
      .map((model) => ({ model: model.id, score: scoreModel(taskWeights, model) }))
      .sort((a, b) => b.score - a.score);

    return ranked[0];
  }, [taskWeights]);

  async function runABTest() {
    const response = await fetch('http://localhost:8787/api/ab-test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(abTest)
    });

    const data = await response.json();
    alert(`Победитель: ${data.winner}`);
  }

  return (
    <main className="layout">
      <section className="card">
        <h1>PromptOps Desktop</h1>
        <p>Хранилище промптов с тегами, версиями и анализом моделей.</p>
        <form onSubmit={savePrompt} className="form-grid">
          <input placeholder="Название" value={prompt.title} onChange={(event) => setPrompt({ ...prompt, title: event.target.value })} required />
          <textarea placeholder="Промпт" value={prompt.content} onChange={(event) => setPrompt({ ...prompt, content: event.target.value })} required />
          <input placeholder="Теги через запятую" value={prompt.tags} onChange={(event) => setPrompt({ ...prompt, tags: event.target.value })} />
          <textarea placeholder="Примеры (один на строку)" value={prompt.examples} onChange={(event) => setPrompt({ ...prompt, examples: event.target.value })} />
          <label>
            Модель
            <select value={prompt.model} onChange={(event) => setPrompt({ ...prompt, model: event.target.value })}>
              {modelProfiles.map((model) => <option key={model.id} value={model.id}>{model.id}</option>)}
            </select>
          </label>
          <button type="submit">Сохранить</button>
        </form>
      </section>

      <section className="card">
        <h2>Процесс анализа и выбора модели</h2>
        <ol className="pipeline">
          <li>1. Анализ задачи и требований.</li>
          <li>2. Подбор кандидатов по метрикам: цена, latency, качество, контекст, мультимодальность.</li>
          <li>3. Рекомендация модели.</li>
          <li>4. A/B тест промптов.</li>
          <li>5. Выбор финальной версии и сохранение истории.</li>
        </ol>

        <div className="weights">
          {Object.entries(taskWeights).map(([key, value]) => (
            <label key={key}>
              {key}
              <input type="range" min="1" max="5" value={value} onChange={(event) => setTaskWeights({ ...taskWeights, [key]: Number(event.target.value) })} />
            </label>
          ))}
        </div>
        <p><strong>Рекомендованная модель:</strong> {recommendation.model} (score: {recommendation.score})</p>
      </section>

      <section className="card">
        <h2>Промпты</h2>
        <ul className="list">
          {prompts.map((item) => (
            <li key={item.id}>
              <button onClick={() => setSelectedPromptId(item.id)}>
                {item.title} · {item.tags.join(', ')}
              </button>
            </li>
          ))}
        </ul>
        {selectedPrompt && (
          <article className="details">
            <h3>{selectedPrompt.title}</h3>
            <p>{selectedPrompt.content}</p>
            <h4>История версий</h4>
            <ul>
              {selectedPrompt.versions.map((version) => (
                <li key={version.version}>v{version.version}: {new Date(version.createdAt).toLocaleString()}</li>
              ))}
            </ul>
          </article>
        )}
      </section>

      <section className="card">
        <h2>A/B тест</h2>
        <div className="form-grid">
          <input placeholder="ID Prompt A" value={abTest.promptA} onChange={(event) => setAbTest({ ...abTest, promptA: event.target.value })} />
          <input placeholder="ID Prompt B" value={abTest.promptB} onChange={(event) => setAbTest({ ...abTest, promptB: event.target.value })} />
          <label>
            Model A
            <select value={abTest.modelA} onChange={(event) => setAbTest({ ...abTest, modelA: event.target.value })}>
              {modelProfiles.map((model) => <option key={model.id} value={model.id}>{model.id}</option>)}
            </select>
          </label>
          <label>
            Model B
            <select value={abTest.modelB} onChange={(event) => setAbTest({ ...abTest, modelB: event.target.value })}>
              {modelProfiles.map((model) => <option key={model.id} value={model.id}>{model.id}</option>)}
            </select>
          </label>
          <button onClick={runABTest}>Запустить A/B тест</button>
        </div>
      </section>
    </main>
  );
}
