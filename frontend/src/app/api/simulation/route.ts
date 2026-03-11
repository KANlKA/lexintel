import { NextRequest, NextResponse } from 'next/server'

type Role = 'judge' | 'opponent' | 'lawyer'
type Mode = 'judge' | 'opponent'
type Side = 'defense' | 'prosecution'

interface Weakness {
  actor: string
  action: string
  weakness_score: number
  severity: 'high' | 'medium' | 'low'
  reasons: string[]
  source_document: string
}

interface Contradiction {
  description: string
  severity: 'critical' | 'moderate' | 'minor'
  event1_summary: string
  event2_summary: string
}

interface Message {
  role: Role
  content: string
}

interface SimulationRequest {
  mode: Mode
  side: Side
  weaknesses: Weakness[]
  contradictions: Contradiction[]
  messages: Message[]
}

interface AnthropicResponse {
  content?: Array<{
    text?: string
  }>
}

function buildSystemPrompt(body: SimulationRequest): string {
  const topWeaknesses = body.weaknesses
    .slice(0, 5)
    .map(
      (item) =>
        `- ${item.actor}: "${item.action}" (score ${item.weakness_score}; reasons: ${item.reasons.join(', ') || 'none'})`,
    )
    .join('\n')

  const topContradictions = body.contradictions
    .slice(0, 3)
    .map((item) => `- ${item.description} [${item.severity}]`)
    .join('\n')

  const aiRole =
    body.mode === 'judge'
      ? 'You are a strict trial judge.'
      : `You are an aggressive ${body.side === 'defense' ? 'prosecutor' : 'defense attorney'}.`

  return `${aiRole}
Question the lawyer tightly and concretely.
Weaknesses:
${topWeaknesses || 'None loaded.'}
Contradictions:
${topContradictions || 'None loaded.'}`
}

function generateFallbackResponse(body: SimulationRequest): string {
  const speaker = body.mode === 'judge' ? 'Judge' : 'Opposing Counsel'
  const lastLawyerMessage = [...body.messages].reverse().find((message) => message.role === 'lawyer')
  const weakness = body.weaknesses[0]
  const contradiction = body.contradictions[0]

  if (body.messages.length <= 1) {
    if (contradiction) {
      return `${speaker}: You rely on two conflicting facts. ${contradiction.description} Reconcile that conflict in one precise answer.`
    }
    if (weakness) {
      return `${speaker}: Your case turns on "${weakness.action}". Why should the court trust that point despite ${weakness.reasons[0] || 'its weakness'}?`
    }
    return `${speaker}: State your strongest factual point in two sentences, then identify the evidentiary support for it.`
  }

  const answer = lastLawyerMessage?.content.trim() || ''
  const shortAnswer = answer.length < 80
  const hedging = /\b(maybe|perhaps|probably|possibly|i think|i believe)\b/i.test(answer)

  if (shortAnswer || hedging) {
    if (contradiction) {
      return `${speaker}: That answer is evasive. Address the contradiction directly: ${contradiction.event1_summary} versus ${contradiction.event2_summary}. Which fact do you want the court to accept, and why?`
    }
    return `${speaker}: That answer lacks precision. Give a specific timeline, actor, and supporting fact.`
  }

  if (weakness) {
    return `${speaker}: You still have not neutralized the weakness in "${weakness.action}". Explain why ${weakness.actor}'s account remains reliable despite ${weakness.reasons.join(', ')}.`
  }

  return `${speaker}: Narrow your answer to the decisive issue. What single fact most strongly supports your position, and what is the best challenge to it?`
}

async function generateAnthropicResponse(body: SimulationRequest): Promise<string | null> {
  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) {
    return null
  }

  const system = buildSystemPrompt(body)
  const messages = body.messages.map((message) => ({
    role: message.role === 'lawyer' ? 'user' : 'assistant',
    content: message.content,
  }))

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: process.env.ANTHROPIC_MODEL ?? 'claude-3-5-sonnet-latest',
        max_tokens: 300,
        system,
        messages,
      }),
      cache: 'no-store',
    })

    if (!response.ok) {
      return null
    }

    const data: AnthropicResponse = await response.json()
    return data.content?.map((block) => block.text ?? '').join('').trim() || null
  } catch {
    return null
  }
}

export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = (await request.json()) as SimulationRequest
  const anthropicText = await generateAnthropicResponse(body)
  const text = anthropicText ?? generateFallbackResponse(body)

  return NextResponse.json({ text })
}
