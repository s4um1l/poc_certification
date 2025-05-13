import dynamic from 'next/dynamic';

// Create a client-side wrapper
const ClientChatWrapper = dynamic(() => import('../components/ClientChatWrapper'), {
  loading: () => <p className="p-8 text-center">Loading chat...</p>,
});

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center p-4 md:p-24">
      <h1 className="text-3xl font-bold mb-8">Shopify Operations AI Assistant</h1>
      <div className="w-full max-w-4xl bg-white rounded-lg shadow-xl overflow-hidden">
        <ClientChatWrapper />
      </div>
    </main>
  );
} 