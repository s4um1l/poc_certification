"use client"

import { useChat, type Message } from "@ai-sdk/react"
import { useRef, useEffect } from "react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, BarChart3, Package, TrendingUp, ShoppingCart, Wrench } from "lucide-react"

// Define a type for our expected tool usage data for clarity
interface ToolCallData {
  tool_name: string;
  tool_input: any;
  status: string;
  result?: any;
  error?: string;
  timestamp: string; // Assuming timestamp is a string, adjust if it's another type
  tool_tracking_id: string;
}

export default function Chat() {
  // API URL from environment variable or fallback to localhost
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: `${API_URL}/api/chat`
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    // console.log("Updated messages array:", messages);
    // if (messagesEndRef.current) {
    //   messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    // }
    console.log("PAGE.TSX: messages array updated. Length:", messages.length);
    messages.forEach((msg, index) => {
      console.log(`PAGE.TSX: Message ${index}: ID=${msg.id}, Role=${msg.role}, Content='${msg.content}', Data=${JSON.stringify(msg.data)}, ToolInvocations=${JSON.stringify(msg.toolInvocations)}`);
    });
  }, [messages])

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-[#f9fafb]">
      {/* Shopify-inspired header */}
      <div className="w-full bg-[#008060] text-white py-4 px-6 flex items-center justify-between shadow-md">
        <div className="flex items-center space-x-2">
          <ShoppingCart className="h-6 w-6" />
          <h1 className="text-xl font-bold">Shopify COO Assistant</h1>
        </div>
        <div className="text-sm opacity-80">Powered by AI</div>
      </div>

      <div className="w-full max-w-5xl p-4 flex-1 flex flex-col">
        <Card className="w-full flex-1 shadow-lg border-0 overflow-hidden bg-white">
          <CardHeader className="bg-white border-b border-gray-100 py-4">
            <CardTitle className="text-[#212b36] flex items-center">
              <span className="bg-[#008060] text-white p-1 rounded-md mr-2">
                <BarChart3 className="h-5 w-5" />
              </span>
              Operations Dashboard
            </CardTitle>
          </CardHeader>

          <CardContent className="h-[calc(100vh-240px)] overflow-y-auto p-0 bg-[#f9fafb]">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6 text-[#637381]">
                <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100 max-w-2xl">
                  <h3 className="text-lg font-medium mb-3 text-[#212b36]">
                    Welcome to your Shopify Operations Assistant
                  </h3>
                  <p className="mb-6">
                    Ask me questions about your store's sales velocity and inventory levels to make data-driven
                    decisions.
                  </p>

                  <div className="grid grid-cols-1 gap-3 w-full">
                    <div className="bg-[#f4f6f8] p-4 rounded-lg">
                      <h4 className="font-medium flex items-center text-[#212b36] mb-2">
                        <TrendingUp className="h-4 w-4 mr-2 text-[#008060]" />
                        Sales Questions
                      </h4>
                      <div className="space-y-2">
                        <Button
                          variant="outline"
                          className="justify-start text-left h-auto py-2 w-full border-[#e3e5e7] hover:bg-[#f1f8f5] hover:border-[#008060] transition-colors"
                          onClick={() =>
                            handleInputChange({
                              target: { value: "What were the total sales for Product ID 'P123' in the last 30 days?" },
                            } as any)
                          }
                        >
                          "What were the total sales for Product ID 'P123' in the last 30 days?"
                        </Button>
                        <Button
                          variant="outline"
                          className="justify-start text-left h-auto py-2 w-full border-[#e3e5e7] hover:bg-[#f1f8f5] hover:border-[#008060] transition-colors"
                          onClick={() =>
                            handleInputChange({
                              target: {
                                value: "What's the average daily sales quantity for 'P123' over the past month?",
                              },
                            } as any)
                          }
                        >
                          "What's the average daily sales quantity for 'P123' over the past month?"
                        </Button>
                      </div>
                    </div>

                    <div className="bg-[#f4f6f8] p-4 rounded-lg">
                      <h4 className="font-medium flex items-center text-[#212b36] mb-2">
                        <Package className="h-4 w-4 mr-2 text-[#008060]" />
                        Inventory Questions
                      </h4>
                      <div className="space-y-2">
                        <Button
                          variant="outline"
                          className="justify-start text-left h-auto py-2 w-full border-[#e3e5e7] hover:bg-[#f1f8f5] hover:border-[#008060] transition-colors"
                          onClick={() =>
                            handleInputChange({
                              target: { value: "How many units of Product ID 'P456' are currently in stock?" },
                            } as any)
                          }
                        >
                          "How many units of Product ID 'P456' are currently in stock?"
                        </Button>
                        <Button
                          variant="outline"
                          className="justify-start text-left h-auto py-2 w-full border-[#e3e5e7] hover:bg-[#f1f8f5] hover:border-[#008060] transition-colors"
                          onClick={() =>
                            handleInputChange({
                              target: {
                                value:
                                  "Estimate the days of stock remaining for 'P456' based on the last 30 days of sales.",
                              },
                            } as any)
                          }
                        >
                          "Estimate the days of stock remaining for 'P456'..."
                        </Button>
                        <Button
                          variant="outline"
                          className="justify-start text-left h-auto py-2 w-full border-[#e3e5e7] hover:bg-[#f1f8f5] hover:border-[#008060] transition-colors"
                          onClick={() =>
                            handleInputChange({
                              target: { value: "List products with less than 10 units in stock." },
                            } as any)
                          }
                        >
                          "List products with less than 10 units in stock."
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6 space-y-4">
                {messages.map((message: Message) => {
                  // For assistant messages, check for and display tool data first
                  if (message.role === 'assistant' && message.data) {
                    const toolCalls = message.data as unknown as ToolCallData[];
                    if (toolCalls && Array.isArray(toolCalls) && toolCalls.length > 0) {
                      // Render tool calls - this part can be a separate component or styled div
                      // For now, just a placeholder to show it's being processed separately
                      // from the main content. We will render this, then the main content below.
                    }
                  }

                  // Main message rendering (user or assistant text)
                  if (message.role === 'user' || message.role === 'assistant') {
                    return (
                      <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div
                          className={`max-w-[80%] rounded-lg p-4 shadow-sm ${
                            message.role === "user"
                              ? "bg-[#008060] text-white"
                              : "bg-white border border-gray-100 text-[#212b36] prose"
                          }`}
                        >
                          {/* Display tool usage data if available for this assistant message */}
                          {message.role === 'assistant' && message.data && Array.isArray(message.data) && (message.data as unknown as ToolCallData[]).length > 0 && (
                            <div className="mb-2 p-2 border-b border-gray-200 text-xs text-gray-600 prose-sm">
                              <div className="font-semibold mb-1">Tools Used:</div>
                              {(message.data as unknown as ToolCallData[]).map((toolCall, index) => (
                                <div key={index} className="flex items-center mb-1 last:mb-0">
                                  <Wrench className="h-3 w-3 mr-2 text-gray-500 flex-shrink-0" />
                                  <span>
                                    <strong>{toolCall.tool_name}</strong>
                                    {toolCall.tool_input && Object.keys(toolCall.tool_input).length > 0 && (
                                      <span className="ml-1 text-gray-500">
                                        (params: {JSON.stringify(toolCall.tool_input)})
                                      </span>
                                    )}
                                  </span>
                                </div>
                              ))}
                            </div>
                          )}
                          {/* Render the main message content */}
                          {message.content && <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>}
                        </div>
                      </div>
                    );
                  }
                  return null; // Fallback for any other message roles (e.g. data if it becomes separate)
                })}
                <div ref={messagesEndRef} />
              </div>
            )}
          </CardContent>

          <CardFooter className="border-t border-gray-100 p-4 bg-white">
            <form onSubmit={handleSubmit} className="flex w-full space-x-2">
              <Input
                value={input}
                onChange={handleInputChange}
                placeholder="Ask about sales velocity or inventory levels..."
                className="flex-grow border-[#d9dbde] focus-visible:ring-[#008060]"
                disabled={isLoading}
              />
              <Button
                type="submit"
                disabled={isLoading}
                className="bg-[#008060] hover:bg-[#004c3f] text-white transition-colors"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing
                  </>
                ) : (
                  "Send"
                )}
              </Button>
            </form>
          </CardFooter>
        </Card>

        <div className="w-full mt-4 text-center text-sm text-[#637381]">
          <p>This assistant uses synthetic data for demonstration purposes.</p>
        </div>
      </div>
    </div>
  )
} 