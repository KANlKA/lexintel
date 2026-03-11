import { NextRequest, NextResponse } from 'next/server'

const REASONING_API_BASE =
  process.env.REASONING_API_BASE_URL ?? 'http://127.0.0.1:8000'

type RouteContext = {
  params: Promise<{
    path: string[]
  }>
}

async function forwardRequest(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  const { path } = await context.params
  const targetPath = path.join('/')
  const targetUrl = new URL(`${REASONING_API_BASE}/${targetPath}`)

  request.nextUrl.searchParams.forEach((value, key) => {
    targetUrl.searchParams.set(key, value)
  })

  const headers = new Headers()
  const contentType = request.headers.get('content-type')
  if (contentType) {
    headers.set('content-type', contentType)
  }

  try {
    const upstreamResponse = await fetch(targetUrl, {
      method: request.method,
      headers,
      body: request.method === 'GET' || request.method === 'HEAD'
        ? undefined
        : await request.text(),
      cache: 'no-store',
    })

    const responseText = await upstreamResponse.text()
    const responseHeaders = new Headers()
    const upstreamContentType = upstreamResponse.headers.get('content-type')

    if (upstreamContentType) {
      responseHeaders.set('content-type', upstreamContentType)
    }

    return new NextResponse(responseText, {
      status: upstreamResponse.status,
      headers: responseHeaders,
    })
  } catch {
    return NextResponse.json(
      {
        detail:
          'Reasoning API is unavailable. Start the backend service on http://127.0.0.1:8000.',
      },
      { status: 503 },
    )
  }
}

export async function GET(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  return forwardRequest(request, context)
}

export async function POST(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  return forwardRequest(request, context)
}

export async function PUT(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  return forwardRequest(request, context)
}

export async function PATCH(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  return forwardRequest(request, context)
}

export async function DELETE(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  return forwardRequest(request, context)
}

export async function OPTIONS(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  return forwardRequest(request, context)
}
