import { Outlet, Link, useLocation } from 'react-router-dom';

export default function Layout() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="relative border-b border-sand-200 overflow-hidden">
        {/* Background image with overlay */}
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: 'url(/marsh.png)' }}
        />
        <div className="absolute inset-0 bg-white/75" />

        {/* Content */}
        <div className="relative max-w-4xl mx-auto px-4 py-6">
          <Link to="/" className="block">
            <h1 className="text-2xl md:text-3xl font-serif text-sea-800 text-center">
              Ipswich Story Weaver
            </h1>
            <p className="text-sm text-gray-600 text-center mt-1 font-sans">
              Daily tales woven from weather, tides, and local news
            </p>
          </Link>

          {/* Navigation */}
          <nav className="flex justify-center gap-6 mt-6 font-sans text-sm">
            <Link
              to="/"
              className={`pb-1 border-b-2 transition-colors ${
                isActive('/')
                  ? 'border-sea-600 text-sea-700'
                  : 'border-transparent text-gray-600 hover:text-sea-600'
              }`}
            >
              Today's Story
            </Link>
            <Link
              to="/archive"
              className={`pb-1 border-b-2 transition-colors ${
                isActive('/archive') || isActive('/chapter')
                  ? 'border-sea-600 text-sea-700'
                  : 'border-transparent text-gray-600 hover:text-sea-600'
              }`}
            >
              Archive
            </Link>
            <Link
              to="/about"
              className={`pb-1 border-b-2 transition-colors ${
                isActive('/about')
                  ? 'border-sea-600 text-sea-700'
                  : 'border-transparent text-gray-600 hover:text-sea-600'
              }`}
            >
              About
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-sand-200 py-6 mt-12">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <p className="text-sm text-gray-500 font-sans">
            A daily narrative for{' '}
            <span className="text-sea-700">Ipswich, Massachusetts</span>
          </p>
          <p className="text-xs text-gray-400 mt-2">
            Stories generated from weather, tides, seasons, and local news from{' '}
            <a
              href="https://thelocalnews.news/category/ipswich/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sea-600 hover:text-sea-700 underline"
            >
              The Local News
            </a>
          </p>
          <p className="text-xs text-gray-400 mt-2">
            <a
              href="/api/story/feed.xml"
              className="text-sea-600 hover:text-sea-700 underline"
            >
              Subscribe via RSS
            </a>
          </p>
        </div>
      </footer>
    </div>
  );
}
