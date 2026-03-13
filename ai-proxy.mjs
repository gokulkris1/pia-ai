export default async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204 });
  }

  const body = await req.json();
  const { engine, messages, system } = body;

  const anthropicKey = Netlify.env.get("ANTHROPIC_API_KEY");
  const openaiKey = Netlify.env.get("OPENAI_API_KEY");

  // Allow user-supplied keys as fallback (sent in request)
  const userAnthropicKey = body.anthropicKey;
  const userOpenaiKey = body.openaiKey;

  try {
    if (engine === "claude") {
      const key = anthropicKey || userAnthropicKey;
      if (!key) return new Response(JSON.stringify({ error: "No Anthropic API key configured" }), { status: 401 });

      const res = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": key,
          "anthropic-version": "2023-06-01"
        },
        body: JSON.stringify({
          model: "claude-sonnet-4-20250514",
          max_tokens: 400,
          system,
          messages
        })
      });
      const data = await res.json();
      return new Response(JSON.stringify(data), {
        status: res.status,
        headers: { "Content-Type": "application/json" }
      });

    } else if (engine === "gpt4o") {
      const key = openaiKey || userOpenaiKey;
      if (!key) return new Response(JSON.stringify({ error: "No OpenAI API key configured" }), { status: 401 });

      const res = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": "Bearer " + key
        },
        body: JSON.stringify({
          model: "gpt-4o",
          max_tokens: 400,
          messages: [{ role: "system", content: system }, ...messages]
        })
      });
      const data = await res.json();
      return new Response(JSON.stringify(data), {
        status: res.status,
        headers: { "Content-Type": "application/json" }
      });
    }

    return new Response(JSON.stringify({ error: "Unknown engine" }), { status: 400 });

  } catch (e) {
    return new Response(JSON.stringify({ error: e.message }), { status: 500 });
  }
};

export const config = {
  path: "/api/ai"
};
