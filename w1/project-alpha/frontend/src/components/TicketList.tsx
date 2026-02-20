import { useState } from 'react';
import { useTickets, useCreateTicket, useUpdateTicket, useDeleteTicket, useCompleteTicket, useUncompleteTicket } from '../hooks/useTickets';
import { useTags } from '../hooks/useTags';
import { TicketCard } from './TicketCard';
import { TicketForm } from './TicketForm';
import { TagFilter } from './TagFilter';
import { SearchBar } from './SearchBar';
import { Button } from './ui/button';
import { Ticket, CreateTicketRequest, UpdateTicketRequest } from '../types';

export function TicketList() {
  const [search, setSearch] = useState('');
  const [selectedTagId, setSelectedTagId] = useState<number | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingTicket, setEditingTicket] = useState<Ticket | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const { data: ticketsData, isLoading } = useTickets({
    search: search || undefined,
    tag_id: selectedTagId || undefined,
  });

  const { data: tagsData } = useTags();
  const createTicket = useCreateTicket();
  const updateTicket = useUpdateTicket();
  const deleteTicket = useDeleteTicket();
  const completeTicket = useCompleteTicket();
  const uncompleteTicket = useUncompleteTicket();

  const handleCreateTicket = async (data: CreateTicketRequest) => {
    await createTicket.mutateAsync(data);
    setShowCreateForm(false);
  };

  const handleUpdateTicket = async (data: CreateTicketRequest) => {
    if (editingTicket) {
      const updateData: UpdateTicketRequest = {
        title: data.title,
        description: data.description,
        tag_ids: data.tag_ids,
      };
      await updateTicket.mutateAsync({ id: editingTicket.id, data: updateData });
      setEditingTicket(null);
    }
  };

  const handleDeleteTicket = async (id: number) => {
    if (confirm('确定要删除这个 Ticket 吗？')) {
      await deleteTicket.mutateAsync(id);
    }
  };

  const tags = tagsData || [];
  const tickets = ticketsData?.items || [];
  const total = ticketsData?.total || 0;

  const hasFilters = search || selectedTagId;

  return (
    <div className="min-h-screen bg-[#F5F5F7]">
      {/* Header - Apple Style */}
      <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-black/5">
        <div className="flex items-center justify-between px-6 py-4 max-w-[1400px] mx-auto">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#007AFF] to-[#5856D6] flex items-center justify-center shadow-lg shadow-blue-500/20">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-[#1D1D1F] tracking-tight">Project Alpha</h1>
          </div>

          {/* Right Section */}
          <div className="flex items-center gap-3">
            <SearchBar onSearch={setSearch} placeholder="搜索..." />
            <Button
              onClick={() => setShowCreateForm(true)}
              className="bg-[#007AFF] hover:bg-[#0071E3] text-white rounded-full px-5 h-9 text-sm font-medium shadow-lg shadow-blue-500/25 transition-all hover:shadow-blue-500/40 hover:scale-[1.02] active:scale-[0.98]"
            >
              <span className="flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                </svg>
                新建
              </span>
            </Button>
          </div>
        </div>
      </header>

      <div className="flex max-w-[1400px] mx-auto">
        {/* Sidebar - Apple Style */}
        <aside className={`${sidebarOpen ? 'w-64' : 'w-0'} shrink-0 transition-all duration-300 overflow-hidden`}>
          <div className="p-4 pt-6">
            <div className="bg-white/60 backdrop-blur-xl rounded-2xl p-4 shadow-xl shadow-black/[0.04] border border-black/5">
              <div className="flex items-center justify-between mb-4 px-1">
                <h2 className="text-xs font-semibold text-[#86868B] uppercase tracking-wider">标签筛选</h2>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-1 rounded-lg hover:bg-[#F5F5F7] text-[#86868B] transition-colors lg:hidden"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <TagFilter
                tags={tags}
                selectedTagId={selectedTagId}
                onSelectTag={setSelectedTagId}
              />
            </div>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 pt-8">
          {/* Status Bar */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <span className="text-2xl font-semibold text-[#1D1D1F]">{total}</span>
              <span className="text-sm text-[#86868B]">个任务</span>
            </div>
            <div className="flex items-center gap-2">
              {!sidebarOpen && (
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="p-2 rounded-xl bg-white shadow-lg shadow-black/[0.04] border border-black/5 text-[#86868B] hover:text-[#1D1D1F] transition-all"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
              )}
              {hasFilters && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setSearch('');
                    setSelectedTagId(null);
                  }}
                  className="text-[#007AFF] hover:bg-blue-50 rounded-full px-4 h-8 text-sm font-medium"
                >
                  清除筛选
                </Button>
              )}
            </div>
          </div>

          {/* Ticket List */}
          {isLoading ? (
            <div className="flex items-center justify-center py-32">
              <div className="flex flex-col items-center gap-4">
                <div className="w-8 h-8 border-2 border-[#007AFF]/20 border-t-[#007AFF] rounded-full animate-spin" />
                <span className="text-sm text-[#86868B]">加载中...</span>
              </div>
            </div>
          ) : tickets.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-32">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#F5F5F7] to-white flex items-center justify-center mb-6 shadow-xl shadow-black/[0.04]">
                <svg className="w-8 h-8 text-[#D1D1D6]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-[#1D1D1F] mb-2">暂无任务</h3>
              <p className="text-sm text-[#86868B] mb-6">点击"新建"创建您的第一个任务</p>
              <Button
                onClick={() => setShowCreateForm(true)}
                className="bg-[#007AFF] hover:bg-[#0071E3] text-white rounded-full px-6 h-10 text-sm font-medium shadow-lg shadow-blue-500/25 transition-all hover:scale-[1.02]"
              >
                创建任务
              </Button>
            </div>
          ) : (
            <div className="grid gap-3">
              {tickets.map((ticket: Ticket) => (
                <TicketCard
                  key={ticket.id}
                  ticket={ticket}
                  onComplete={(id) => completeTicket.mutate(id)}
                  onUncomplete={(id) => uncompleteTicket.mutate(id)}
                  onEdit={setEditingTicket}
                  onDelete={handleDeleteTicket}
                />
              ))}
            </div>
          )}
        </main>
      </div>

      {/* Create Dialog - Apple Style */}
      {showCreateForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/20 backdrop-blur-sm animate-fade-in"
            onClick={() => setShowCreateForm(false)}
          />
          <div className="relative bg-white rounded-2xl shadow-2xl shadow-black/[0.15] w-full max-w-lg overflow-hidden animate-scale-in">
            <div className="px-6 py-4 border-b border-black/5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[#1D1D1F]">新建任务</h2>
              <button
                onClick={() => setShowCreateForm(false)}
                className="p-1.5 rounded-full hover:bg-[#F5F5F7] text-[#86868B] transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6">
              <TicketForm
                tags={tags}
                onSubmit={handleCreateTicket}
                onCancel={() => setShowCreateForm(false)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Edit Dialog - Apple Style */}
      {editingTicket && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/20 backdrop-blur-sm animate-fade-in"
            onClick={() => setEditingTicket(null)}
          />
          <div className="relative bg-white rounded-2xl shadow-2xl shadow-black/[0.15] w-full max-w-lg overflow-hidden animate-scale-in">
            <div className="px-6 py-4 border-b border-black/5 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[#1D1D1F]">编辑任务</h2>
              <button
                onClick={() => setEditingTicket(null)}
                className="p-1.5 rounded-full hover:bg-[#F5F5F7] text-[#86868B] transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6">
              <TicketForm
                ticket={editingTicket}
                tags={tags}
                onSubmit={handleUpdateTicket}
                onCancel={() => setEditingTicket(null)}
              />
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes fade-in {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes scale-in {
          from { opacity: 0; transform: scale(0.95); }
          to { opacity: 1; transform: scale(1); }
        }
        .animate-fade-in {
          animation: fade-in 0.2s ease-out;
        }
        .animate-scale-in {
          animation: scale-in 0.25s ease-out;
        }
      `}</style>
    </div>
  );
}
