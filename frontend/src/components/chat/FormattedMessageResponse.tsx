import React from 'react';
import { Shield, Users, ClipboardList, Info, FileText } from 'lucide-react';

interface FormattedMessageResponseProps {
  content: string;
}

export const FormattedMessageResponse: React.FC<FormattedMessageResponseProps> = ({ content }) => {
  if (!content) return null;

  const lines = content.split('\n');
  const blocks: React.ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // 1. Section Header: ### or #### with Icon
    if (trimmed.startsWith('###') || trimmed.startsWith('####')) {
      const headerText = trimmed.replace(/^#+\s*/, '');
      let iconNode: React.ReactNode = null;

      if (headerText.includes('Purpose') || headerText.includes('Scope') || headerText.includes('🛡️')) {
        iconNode = <Shield className="w-4 h-4 text-emerald-700 dark:text-emerald-400 shrink-0 mt-0.5" />;
      } else if (headerText.includes('Roles') || headerText.includes('Functions') || headerText.includes('👥')) {
        iconNode = <Users className="w-4 h-4 text-emerald-700 dark:text-emerald-400 shrink-0 mt-0.5" />;
      } else if (headerText.includes('Considerations') || headerText.includes('Safety') || headerText.includes('📋')) {
        iconNode = <ClipboardList className="w-4 h-4 text-emerald-700 dark:text-emerald-400 shrink-0 mt-0.5" />;
      } else {
        iconNode = <FileText className="w-4 h-4 text-emerald-700 dark:text-emerald-400 shrink-0 mt-0.5" />;
      }

      const cleanTitle = headerText.replace(/^[🛡️👥📋📄📍📊🔍💻📌🏢]\s*/, '').trim();

      blocks.push(
        <div key={`header-${i}`} className="flex items-center gap-2 pt-3 pb-1 border-b border-slate-100 dark:border-slate-800 font-bold text-slate-900 dark:text-slate-100 text-sm">
          {iconNode}
          <span>{cleanTitle}</span>
        </div>
      );
      i++;
      continue;
    }

    // 2. Callout Info Box: > ℹ️ ...
    if (trimmed.startsWith('>') || trimmed.includes('This analysis is based on')) {
      const calloutText = trimmed.replace(/^>\s*/, '').replace(/^[ℹ️]\s*/, '').trim();
      blocks.push(
        <div key={`callout-${i}`} className="bg-sky-50 dark:bg-sky-950/40 border border-sky-200/80 dark:border-sky-800/60 rounded-xl p-3.5 flex items-start gap-3 my-3 text-sky-900 dark:text-sky-200 text-xs shadow-2xs">
          <Info className="w-4 h-4 text-sky-600 dark:text-sky-400 shrink-0 mt-0.5" />
          <p className="leading-relaxed font-medium">{calloutText}</p>
        </div>
      );
      i++;
      continue;
    }

    // 3. Markdown Table Parser: | Header | Header |
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const tableRows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        const rowLine = lines[i].trim();
        // Skip separator row |---|---|
        if (!rowLine.includes('---')) {
          const cells = rowLine.split('|').slice(1, -1).map((c) => c.trim());
          tableRows.push(cells);
        }
        i++;
      }

      if (tableRows.length > 0) {
        const headerRow = tableRows[0];
        const bodyRows = tableRows.slice(1);

        blocks.push(
          <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 shadow-2xs bg-white dark:bg-slate-900">
            <table className="w-full text-left text-xs border-collapse font-sans">
              <thead>
                <tr className="bg-slate-100/80 dark:bg-slate-800/80 border-b border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 font-extrabold">
                  {headerRow.map((cell, hIdx) => (
                    <th key={hIdx} className="px-4 py-2.5 uppercase text-[10px] tracking-wider text-slate-600 dark:text-slate-400">
                      {cell}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300 font-medium">
                {bodyRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className={`px-4 py-2.5 ${cIdx === 0 ? 'font-bold text-slate-800 dark:text-slate-200' : 'text-slate-600 dark:text-slate-300'}`}>
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // 4. Bullet list item: - ... or * ...
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const bulletItems: string[] = [];
      while (i < lines.length && (lines[i].trim().startsWith('- ') || lines[i].trim().startsWith('* '))) {
        bulletItems.push(lines[i].trim().replace(/^[-*]\s*/, ''));
        i++;
      }

      blocks.push(
        <ul key={`list-${i}`} className="space-y-1.5 my-2 pl-1 text-slate-700 dark:text-slate-300 text-xs">
          {bulletItems.map((item, bIdx) => {
            const parts = item.split(/(\*\*.*?\*\*)/g);
            return (
              <li key={bIdx} className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-700 dark:bg-emerald-400 shrink-0 mt-1.5" />
                <span className="leading-relaxed">
                  {parts.map((p, pIdx) =>
                    p.startsWith('**') && p.endsWith('**') ? (
                      <strong key={pIdx} className="font-extrabold text-slate-900 dark:text-slate-100">
                        {p.slice(2, -2)}
                      </strong>
                    ) : (
                      p
                    )
                  )}
                </span>
              </li>
            );
          })}
        </ul>
      );
      continue;
    }

    // 5. Standard Paragraph Text
    const paragraphText = trimmed;
    const formattedParts = paragraphText.split(/(\*\*.*?\*\*)/g);
    blocks.push(
      <p key={`p-${i}`} className="leading-relaxed text-slate-700 dark:text-slate-300 text-xs my-1 font-sans">
        {formattedParts.map((p, pIdx) =>
          p.startsWith('**') && p.endsWith('**') ? (
            <strong key={pIdx} className="font-extrabold text-slate-900 dark:text-slate-100">
              {p.slice(2, -2)}
            </strong>
          ) : (
            p
          )
        )}
      </p>
    );

    i++;
  }

  return <div className="space-y-2">{blocks}</div>;
};

