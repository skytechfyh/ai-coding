import { Tag } from '../types';

interface TagFilterProps {
  tags: Tag[];
  selectedTagId: number | null;
  onSelectTag: (tagId: number | null) => void;
}

export function TagFilter({ tags, selectedTagId, onSelectTag }: TagFilterProps) {
  return (
    <div className="space-y-0.5">
      <button
        onClick={() => onSelectTag(null)}
        className={`
          w-full text-left px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-200
          ${selectedTagId === null
            ? 'bg-gradient-to-r from-[#007AFF] to-[#5856D6] text-white shadow-lg shadow-blue-500/25'
            : 'text-[#86868B] hover:bg-[#F5F5F7] hover:text-[#1D1D1F]'
          }
        `}
      >
        全部任务
      </button>
      {tags.map((tag) => (
        <button
          key={tag.id}
          onClick={() => onSelectTag(tag.id)}
          className={`
            w-full text-left px-3 py-2 rounded-xl text-[13px] font-medium transition-all duration-200
            flex items-center gap-2.5
            ${selectedTagId === tag.id
              ? 'bg-gradient-to-r from-[#007AFF] to-[#5856D6] text-white shadow-lg shadow-blue-500/25'
              : 'text-[#86868B] hover:bg-[#F5F5F7] hover:text-[#1D1D1F]'
            }
          `}
        >
          <span
            className={`w-2.5 h-2.5 rounded-full transition-transform duration-200 ${selectedTagId === tag.id ? 'scale-110' : ''}`}
            style={{ backgroundColor: tag.color }}
          />
          {tag.name}
        </button>
      ))}
    </div>
  );
}
