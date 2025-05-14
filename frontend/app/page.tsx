"use client"

import { useChat } from "@ai-sdk/react"
import { useRef, useEffect } from "react"
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, BarChart3, Package, TrendingUp, ShoppingCart } from "lucide-react"

export default function Chat() {
  // TEMPORARY HARDCODING FOR TESTING - REMOVE LATER
  const API_URL = "https://poccertification-production.up.railway.app";
  // const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"; // Original line

  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: `${API_URL}/api/chat` // Configure the API endpoint
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" })
    }
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
                              target: { value: "Which of my top-selling products are at risk of running out of stock soon?" },
                            } as any)
                          }
                        >
                          "Which of my top-selling products are at risk of running out of stock soon?"
                        </Button>
                        <Button
                          variant="outline"
                          className="justify-start text-left h-auto py-2 w-full border-[#e3e5e7] hover:bg-[#f1f8f5] hover:border-[#008060] transition-colors"
                          onClick={() =>
                            handleInputChange({
                              target: {
                                value: "Compare the sales and inventory status of my top 3 selling Apparel products",
                              },
                            } as any)
                          }
                        >
                          "Compare the sales and inventory status of my top 3 selling Apparel products"
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
                              target: { value: "For products in the Electronics category, show me inventory levels and recent sales performance" },
                            } as any)
                          }
                        >
                          "For products in the Electronics category, show me inventory levels and recent sales performance"
                        </Button>
                        <Button
                          variant="outline"
                          className="justify-start text-left h-auto py-2 w-full border-[#e3e5e7] hover:bg-[#f1f8f5] hover:border-[#008060] transition-colors"
                          onClick={() =>
                            handleInputChange({
                              target: {
                                value:
                                  "What's my overall inventory health - show me products with critical stock levels and their sales performance",
                              },
                            } as any)
                          }
                        >
                          "What's my overall inventory health - show me products with critical stock levels and their sales performance"
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
                {messages.map((message) => (
                  <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-[80%] rounded-lg p-4 shadow-sm ${
                        message.role === "user"
                          ? "bg-[#008060] text-white"
                          : "bg-white border border-gray-100 text-[#212b36] prose"
                      }`}
                    >
                      {message.role === 'user' ? (
                        message.content
                      ) : (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                      )}
                    </div>
                  </div>
                ))}
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