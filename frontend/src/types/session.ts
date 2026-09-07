export interface CitationSource {
  title: string;
  category: string;
  meta: string;
  badge: 'Uploaded' | 'Trusted' | 'Verified';
  badgeType: 'uploaded' | 'trusted' | 'verified';
}

export interface ReasoningStep {
  id: string;
  label: string;
  icon: string;
  status: 'pending' | 'active' | 'done' | 'error';
  duration?: number;
  detail?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  timestamp: string;
  attachedFile?: { name: string; size: string };
  isInitialAnalysis?: boolean;
  steps?: string[];
  sources?: CitationSource[];
  findings?: { id: number; text: string }[];
  confidence?: 'High' | 'Medium' | 'Low';
  reasoningSteps?: ReasoningStep[];
  reasoningDuration?: number;
}

export interface ChatSession {
  id: string;
  title: string;
  time: string;
  messages: ChatMessage[];
}
