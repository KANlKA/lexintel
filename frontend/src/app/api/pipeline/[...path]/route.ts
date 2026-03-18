import { NextRequest, NextResponse } from 'next/server'

const PIPELINE_API_BASE =
  process.env.PIPELINE_API_BASE_URL ?? 'http://127.0.0.1:8001'

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
  const targetUrl = new URL(`${PIPELINE_API_BASE}/${targetPath}`)

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
      body:
        request.method === 'GET' || request.method === 'HEAD'
          ? undefined
          : await request.arrayBuffer(),
      cache: 'no-store',
    })

    const responseBuffer = await upstreamResponse.arrayBuffer()
    const responseHeaders = new Headers()
    const upstreamContentType = upstreamResponse.headers.get('content-type')

    if (upstreamContentType) {
      responseHeaders.set('content-type', upstreamContentType)
    }

    return new NextResponse(responseBuffer, {
      status: upstreamResponse.status,
      headers: responseHeaders,
    })
  } catch (error) {
    console.error('Pipeline API proxy failed', {
      targetUrl: targetUrl.toString(),
      method: request.method,
      error,
    })

    return NextResponse.json(
      {
        detail:
          `Document pipeline API is unavailable at ${PIPELINE_API_BASE}. Start the backend service or set PIPELINE_API_BASE_URL.`,
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
