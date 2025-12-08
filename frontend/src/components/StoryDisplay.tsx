import type { StoryChapter, NewsItemBrief } from '../api/types';

interface StoryDisplayProps {
  chapter: StoryChapter;
  showMeta?: boolean;
}

export default function StoryDisplay({ chapter, showMeta = true }: StoryDisplayProps) {
  // Split body into paragraphs
  const paragraphs = chapter.body.split('\n\n').filter(p => p.trim());

  return (
    <article className="prose-story">
      {/* Title */}
      <header className="mb-8">
        <h2 className="text-2xl md:text-3xl font-serif text-sea-800 mb-2">
          {chapter.title}
        </h2>
        <p className="text-sm text-gray-500 font-sans">
          {chapter.day_of_week}, {chapter.month_name} {new Date(chapter.chapter_date + 'T12:00:00').getDate()},{' '}
          {new Date(chapter.chapter_date + 'T12:00:00').getFullYear()}
        </p>
      </header>

      {/* Story Body */}
      <div className="space-y-6">
        {paragraphs.map((paragraph, index) => (
          <p key={index} className="text-lg leading-relaxed text-gray-700">
            {paragraph}
          </p>
        ))}
      </div>

      {/* Metadata */}
      {showMeta && (
        <footer className="mt-10 pt-6 border-t border-sand-200">
          <div className="flex flex-wrap gap-4 text-sm text-gray-500 font-sans">
            {chapter.weather_summary && (
              <span className="flex items-center gap-1">
                <WeatherIcon />
                {chapter.weather_summary}
              </span>
            )}
            {chapter.tide_state && (
              <span className="flex items-center gap-1">
                <TideIcon />
                Tide: {chapter.tide_state}
              </span>
            )}
            <span className="flex items-center gap-1">
              <SeasonIcon />
              {chapter.season}
            </span>
          </div>

          {/* News items that shaped this chapter */}
          <div className="mt-6">
            <h4 className="text-sm font-sans font-medium text-gray-600 mb-3 flex items-center gap-2">
              <NewspaperIcon />
              News that shaped this chapter
            </h4>
            {chapter.news_items && chapter.news_items.length > 0 ? (
              <div className="space-y-3">
                {chapter.news_items.map((news: NewsItemBrief) => (
                  <div
                    key={news.id}
                    className="pl-4 border-l-2 border-sea-300 text-sm"
                  >
                    <p className="font-medium text-gray-700">{news.headline}</p>
                    <p className="text-gray-500 mt-1">
                      {news.summary.length > 120
                        ? news.summary.slice(0, 120) + '...'
                        : news.summary}
                    </p>
                    <a
                      href={news.article_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sea-600 hover:text-sea-700 text-xs mt-1 inline-flex items-center gap-1"
                    >
                      Read on The Local News
                      <ExternalLinkIcon />
                    </a>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500 italic pl-4 border-l-2 border-gray-200">
                No local news stories for Ipswich, MA were published at the time today's story automation ran.
              </p>
            )}
          </div>
        </footer>
      )}
    </article>
  );
}

function WeatherIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z"
      />
    </svg>
  );
}

function TideIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M14 10l-2 1m0 0l-2-1m2 1v2.5M20 7l-2 1m2-1l-2-1m2 1v2.5M14 4l-2-1-2 1M4 7l2-1M4 7l2 1M4 7v2.5M12 21l-2-1m2 1l2-1m-2 1v-2.5M6 18l-2-1v-2.5M18 18l2-1v-2.5"
      />
    </svg>
  );
}

function SeasonIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
      />
    </svg>
  );
}

function NewspaperIcon() {
  return (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"
      />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
      />
    </svg>
  );
}
