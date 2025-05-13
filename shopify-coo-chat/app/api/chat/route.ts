import { openai } from "@ai-sdk/openai"
import { streamText } from "ai"

// Allow streaming responses up to 30 seconds
export const maxDuration = 30

export async function POST(req: Request) {
  const { messages } = await req.json()

  // Create a system message to define the AI's role as a COO assistant
  const systemMessage = {
    role: "system",
    content: `You are an AI COO assistant for Shopify merchants with $1M-$20M in revenue.
You specialize in answering operational questions related to sales velocity and inventory levels.
You can help with questions like:
- Total sales for specific products in time periods
- Current inventory levels for products
- Average daily sales quantities
- Estimating days of stock remaining based on sales velocity
- Identifying low stock products

Present your responses in a structured format with clear sections and bullet points when appropriate.
Use a professional but friendly tone, as if you're a trusted operations advisor.
Include specific metrics and data points in your responses.
If asked about something outside your expertise, politely redirect to your areas of focus.
When making recommendations, be specific and actionable.`,
  }

  // Add the system message to the beginning of the messages array
  const messagesWithSystem = [systemMessage, ...messages]

  const result = streamText({
    model: openai("gpt-4o"),
    messages: messagesWithSystem,
  })

  return result.toDataStreamResponse()
}
