export default async (req) => {
  const body = await req.json();
  const { action, engine, messages, system, text, voiceId } = body;

  // ElevenLabs TTS
  if (action === 'tts') {
    const key = Netlify.env.get('ELEVENLABS_API_KEY');
    if (!key) return new Response(JSON.stringify({ error: 'No ElevenLabs key' }), { status: 401, headers: { 'Content-Type': 'application/json' } });
    const vid = voiceId || '21m00Tcm4TlvDq8ikWAM';
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${vid}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'xi-api-key': key },
      body: JSON.stringify({ text, model_id: 'eleven_monolingual_v1', voice_settings: { stability: 0.5, similarity_boost: 0.75 } })
    });
    if (!res.ok) return new Response(JSON.stringify({ error: 'ElevenLabs error' }), { status: res.status, headers: { 'Content-Type': 'application/json' } });
    const audio = await res.arrayBuffer();
    return new Response(audio, { status: 200, headers: { 'Content-Type': 'audio/mpeg' } });
  }

  // Claude
  if (engine === 'claude') {
    const key = Netlify.env.get('calude_key');
    if (!key) return new Response(JSON.stringify({ error: 'No Anthropic key configured' }), { status: 401, headers: { 'Content-Type': 'application/json' } });
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01' },
      body: JSON.stringify({ model: 'claude-sonnet-4-6', max_tokens: 400, system, messages })
    });
    const data = await res.json();
    return new Response(JSON.stringify(data), { status: res.status, headers: { 'Content-Type': 'application/json' } });
  }

  // GPT-4o
  if (engine === 'gpt4o') {
    const key = Netlify.env.get('OpenAI_Key');
    if (!key) return new Response(JSON.stringify({ error: 'No OpenAI key configured' }), { status: 401, headers: { 'Content-Type': 'application/json' } });
    const res = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key },
      body: JSON.stringify({ model: 'gpt-4o', max_tokens: 400, messages: [{ role: 'system', content: system }, ...messages] })
    });
    const data = await res.json();
    return new Response(JSON.stringify(data), { status: res.status, headers: { 'Content-Type': 'application/json' } });
  }

  return new Response(JSON.stringify({ error: 'Unknown action' }), { status: 400, headers: { 'Content-Type': 'application/json' } });
};

export const config = { path: '/api/ai' };
