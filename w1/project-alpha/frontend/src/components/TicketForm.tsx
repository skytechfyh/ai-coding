import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Ticket, Tag, CreateTicketRequest } from '../types';

const ticketSchema = z.object({
  title: z.string().min(1, '标题不能为空').max(255),
  description: z.string().max(5000).optional(),
  tag_ids: z.array(z.number()).optional(),
});

interface TicketFormProps {
  ticket?: Ticket | null;
  tags: Tag[];
  onSubmit: (data: CreateTicketRequest) => void;
  onCancel: () => void;
}

export function TicketForm({ ticket, tags, onSubmit, onCancel }: TicketFormProps) {
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<CreateTicketRequest>({
    resolver: zodResolver(ticketSchema),
    defaultValues: {
      title: ticket?.title || '',
      description: ticket?.description || '',
      tag_ids: ticket?.tags.map(t => t.id) || [],
    },
  });

  const selectedTagIds = watch('tag_ids') || [];

  const toggleTag = (tagId: number) => {
    const current = selectedTagIds;
    if (current.includes(tagId)) {
      setValue('tag_ids', current.filter(id => id !== tagId));
    } else {
      setValue('tag_ids', [...current, tagId]);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div>
        <label className="block text-[13px] font-medium text-[#86868B] mb-2">标题</label>
        <input
          {...register('title')}
          className="w-full h-11 px-4 rounded-xl bg-[#F5F5F7] border-0 text-[15px] text-[#1D1D1F] placeholder-[#86868B] focus:outline-none focus:ring-2 focus:ring-[#007AFF]/30 focus:bg-white transition-all duration-200"
          placeholder="输入任务标题"
        />
        {errors.title && (
          <p className="text-[13px] text-[#FF3B30] mt-2 flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {errors.title.message}
          </p>
        )}
      </div>

      <div>
        <label className="block text-[13px] font-medium text-[#86868B] mb-2">描述</label>
        <textarea
          {...register('description')}
          className="w-full px-4 py-3 rounded-xl bg-[#F5F5F7] border-0 text-[15px] text-[#1D1D1F] placeholder-[#86868B] focus:outline-none focus:ring-2 focus:ring-[#007AFF]/30 focus:bg-white transition-all duration-200 min-h-[120px] resize-none"
          placeholder="添加任务描述（可选）"
        />
      </div>

      <div>
        <label className="block text-[13px] font-medium text-[#86868B] mb-2">标签</label>
        <div className="flex gap-2 flex-wrap">
          {tags.map((tag) => (
            <button
              key={tag.id}
              type="button"
              onClick={() => toggleTag(tag.id)}
              className={`
                px-3.5 py-1.5 rounded-full text-[12px] font-medium transition-all duration-200
                ${selectedTagIds.includes(tag.id)
                  ? 'shadow-lg shadow-black/10 scale-105'
                  : 'opacity-70 hover:opacity-100 hover:scale-105'
                }
              `}
              style={{
                backgroundColor: tag.color,
                color: '#fff',
              }}
            >
              {tag.name}
              {selectedTagIds.includes(tag.id) && (
                <span className="ml-1.5">×</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-4">
        <button
          type="button"
          onClick={onCancel}
          className="h-10 px-5 rounded-full text-[14px] font-medium text-[#86868B] hover:bg-[#F5F5F7] hover:text-[#1D1D1F] transition-all duration-200"
        >
          取消
        </button>
        <button
          type="submit"
          className="h-10 px-6 rounded-full text-[14px] font-medium bg-[#007AFF] hover:bg-[#0071E3] text-white shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
        >
          {ticket ? '保存修改' : '创建任务'}
        </button>
      </div>
    </form>
  );
}
