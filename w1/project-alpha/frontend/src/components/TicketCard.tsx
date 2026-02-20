import { Ticket } from '../types';
import { formatDate } from '../lib/utils';

interface TicketCardProps {
  ticket: Ticket;
  onComplete: (id: number) => void;
  onUncomplete: (id: number) => void;
  onEdit: (ticket: Ticket) => void;
  onDelete: (id: number) => void;
}

export function TicketCard({ ticket, onComplete, onUncomplete, onEdit, onDelete }: TicketCardProps) {
  const isCompleted = ticket.status === 'completed';

  return (
    <div
      className={`
        group relative bg-white rounded-2xl p-5 shadow-lg shadow-black/[0.04]
        border border-black/[0.04] hover:border-black/[0.08]
        transition-all duration-300 ease-out
        hover:shadow-xl hover:shadow-black/[0.06]
        hover:scale-[1.01] active:scale-[0.99]
        ${isCompleted ? 'bg-gradient-to-r from-[#F5F5F7] to-white' : 'bg-white'}
      `}
    >
      {/* Completion Toggle */}
      <button
        onClick={() => isCompleted ? onUncomplete(ticket.id) : onComplete(ticket.id)}
        className={`
          absolute top-5 left-5 w-5 h-5 rounded-full border-2
          transition-all duration-200 ease-out
          ${isCompleted
            ? 'bg-gradient-to-br from-[#34C759] to-[#30B350] border-transparent scale-100'
            : 'border-[#D1D1D6] hover:border-[#007AFF] hover:scale-110'
          }
          flex items-center justify-center
        `}
      >
        {isCompleted && (
          <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
      </button>

      <div className="pl-8">
        {/* Tags */}
        <div className="flex gap-1.5 mb-2.5 flex-wrap">
          {ticket.tags.map((tag) => (
            <span
              key={tag.id}
              className="px-2.5 py-0.5 rounded-full text-[10px] font-medium tracking-wide"
              style={{
                backgroundColor: `${tag.color}15`,
                color: tag.color,
              }}
            >
              {tag.name}
            </span>
          ))}
        </div>

        {/* Title */}
        <h3
          className={`
            text-[15px] leading-relaxed font-medium mb-1.5 tracking-[-0.01em]
            transition-colors duration-200
            ${isCompleted
              ? 'text-[#86868B] line-through decoration-1'
              : 'text-[#1D1D1F] group-hover:text-[#007AFF]'
            }
          `}
        >
          {ticket.title}
        </h3>

        {/* Description */}
        {ticket.description && (
          <p
            className={`
              text-[13px] leading-relaxed mb-4 line-clamp-2
              ${isCompleted ? 'text-[#AEAEB2]' : 'text-[#86868B]'}
            `}
          >
            {ticket.description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-[#AEAEB2] font-medium">
            {formatDate(ticket.created_at)}
          </span>

          {/* Actions */}
          <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <button
              onClick={() => onEdit(ticket)}
              className="p-1.5 rounded-lg hover:bg-[#F5F5F7] text-[#86868B] hover:text-[#1D1D1F] transition-colors"
              title="编辑"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </button>
            <button
              onClick={() => onDelete(ticket.id)}
              className="p-1.5 rounded-lg hover:bg-red-50 text-[#86868B] hover:text-[#FF3B30] transition-colors"
              title="删除"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
