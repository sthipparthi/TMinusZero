import React, { useEffect, useState, useRef } from "react";
import { Helmet, HelmetProvider } from "react-helmet-async";
import dayjs from "dayjs";
import "./SpaceBackground.css";
import LaunchCard from "./components/LaunchCard";
import Modal from "./components/Modal";

// Constants
const TAB_SCROLL_AMOUNT = 200;
const LAUNCH_CARD_SCROLL_AMOUNT = 176; // Card width (160px) + gap (16px)
const AUTO_SCROLL_INTERVAL_MS = 2000;
const AUTO_SCROLL_RESTART_DELAY_MS = 1000;
const MAX_LAUNCHES = 15;

function App() {
  const [articles, setArticles] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [location, setLocation] = useState("Getting location...");
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [selectedLaunch, setSelectedLaunch] = useState(null);
  const [activeTab, setActiveTab] = useState("Space News");
  const [showScrollButtons, setShowScrollButtons] = useState(false);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);
  const [upcomingLaunches, setUpcomingLaunches] = useState([]);
  const [showLaunchScrollButtons, setShowLaunchScrollButtons] = useState(false);

  const tabsContainerRef = useRef(null);
  const launchCarouselRef = useRef(null);
  const autoScrollIntervalRef = useRef(null);

  // Space agencies tabs
  const spaceAgencies = [
    { id: "all", name: "Space News" },
    { id: "isro", name: "ISRO" },
    { id: "nasa", name: "NASA" },
    { id: "spacex", name: "SpaceX" },
    { id: "cnsa", name: "CNSA" },
    { id: "jaxa", name: "JAXA" },
    { id: "esa", name: "ESA" },
    { id: "csa", name: "CSA" },
    { id: "roscosmos", name: "Roscosmos" },
    { id: "blue-origin", name: "Blue Origin" },
    { id: "virgin-galactic", name: "Virgin Galactic" },
    { id: "rocket-lab", name: "Rocket Lab" }
  ];

  // Fetch from local JSON file in /public
  const apiUrl = process.env.PUBLIC_URL + "/space_news.json";

  const fetchArticles = React.useCallback(async () => {
    try {
      const res = await fetch(apiUrl + "?t=" + Date.now()); // Cache-busting
      const data = await res.json();
      setArticles(data || []); // Expecting an array, not { results: [] }
    } catch (error) {
      console.error("Error fetching articles:", error);
      // Demo fallback data
      setArticles([
        {
          id: 1,
          title: "SpaceX Successfully Launches Starship to Orbit",
          summary:
            "SpaceX has achieved a major milestone with the successful orbital launch of its Starship vehicle, marking a significant step forward in space exploration and Mars colonization efforts.",
          url: "https://example.com/spacex-starship",
          image_url:
            "https://images.unsplash.com/photo-1517976487492-5750f3195933?w=400&h=300&fit=crop",
          authors: [{ name: "Space Reporter" }],
          published_at: "2025-08-06T10:30:00Z",
        },
        {
          id: 2,
          title: "NASA's Artemis Mission Prepares for Moon Landing",
          summary:
            "NASA continues preparations for the upcoming Artemis mission that will return humans to the Moon for the first time since the Apollo program ended in 1972.",
          url: "https://example.com/artemis-mission",
          image_url:
            "https://images.unsplash.com/photo-1446776877081-d282a0f896e2?w=400&h=300&fit=crop",
          authors: [{ name: "NASA News" }],
          published_at: "2025-08-05T14:20:00Z",
        },
        {
          id: 3,
          title: "Private Space Station Development Accelerates",
          summary:
            "Multiple companies are racing to develop commercial space stations as the International Space Station approaches the end of its operational life in the coming decade.",
          url: "https://example.com/private-space-station",
          image_url:
            "https://images.unsplash.com/photo-1614728894747-a83421e2b9c9?w=400&h=300&fit=crop",
          authors: [{ name: "Commercial Space News" }],
          published_at: "2025-08-04T09:15:00Z",
        },
      ]);
    }
  }, [apiUrl]);

  const fetchUpcomingLaunches = React.useCallback(async () => {
    try {
      const res = await fetch(process.env.PUBLIC_URL + "/upcoming_events.json?t=" + Date.now());
      const data = await res.json();
      // Extract launches from the wrapped data structure
      const launches = data.launches || [];
      setUpcomingLaunches(launches.slice(0, MAX_LAUNCHES));
    } catch (error) {
      console.error("Error fetching upcoming launches:", error);
      setUpcomingLaunches([]); // Set empty array on error
    }
  }, []);

  const getLocation = async () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        async (position) => {
          try {
            const { latitude, longitude } = position.coords;
            const response = await fetch(
              `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=en`
            );
            const data = await response.json();
            setLocation(
              `${data.city || data.locality || "Unknown"}, ${
                data.countryCode || ""
              }`
            );
          } catch (error) {
            console.error("Error getting location name:", error);
            setLocation("Location unavailable");
          }
        },
        (error) => {
          console.error("Error getting location:", error);
          setLocation("Location unavailable");
        }
      );
    } else {
      setLocation("Geolocation not supported");
    }
  };

  useEffect(() => {
    fetchArticles();
    getLocation();
    fetchUpcomingLaunches();

    const articleInterval = setInterval(fetchArticles, 60 * 60 * 1000); // Hourly
    const launchInterval = setInterval(fetchUpcomingLaunches, 30 * 60 * 1000); // Every 30 minutes
    const clockInterval = setInterval(
      () => setCurrentTime(new Date()),
      1000
    ); // Every second

    return () => {
      clearInterval(articleInterval);
      clearInterval(launchInterval);
      clearInterval(clockInterval);
    };
  }, [fetchArticles, fetchUpcomingLaunches]);

  // Scroll tabs horizontally
  const scrollTabs = (direction) => {
    const container = tabsContainerRef.current;
    if (container) {
      container.scrollBy({
        left: direction === 'left' ? -TAB_SCROLL_AMOUNT : TAB_SCROLL_AMOUNT,
        behavior: 'smooth'
      });

      // Update scroll button states after scrolling
      setTimeout(() => checkScrollButtonStates(), 100);
    }
  };

  // Check scroll button states based on current scroll position
  const checkScrollButtonStates = React.useCallback(() => {
    const container = tabsContainerRef.current;
    if (container) {
      const scrollLeft = container.scrollLeft;
      const maxScroll = container.scrollWidth - container.clientWidth;

      setCanScrollLeft(scrollLeft > 0);
      setCanScrollRight(scrollLeft < maxScroll);
    }
  }, []);

  // Check if tabs container has overflow
  const checkTabsOverflow = React.useCallback(() => {
    const container = tabsContainerRef.current;
    if (container) {
      const hasOverflow = container.scrollWidth > container.clientWidth;
      setShowScrollButtons(hasOverflow);

      // Also check scroll button states
      if (hasOverflow) {
        checkScrollButtonStates();
      }
    }
  }, [checkScrollButtonStates]);

  // Launch carousel scroll functions with continuous looping
  const scrollLaunches = React.useCallback((direction) => {
    const container = launchCarouselRef.current;
    if (container) {
      const currentScroll = container.scrollLeft;
      const halfPoint = container.scrollWidth / 2;

      if (direction === 'right') {
        if (currentScroll >= halfPoint) {
          // When past halfway point, reset to beginning for seamless loop
          container.scrollLeft = currentScroll - halfPoint;
        }
        container.scrollBy({
          left: LAUNCH_CARD_SCROLL_AMOUNT,
          behavior: 'smooth'
        });
      } else if (direction === 'left') {
        if (currentScroll <= LAUNCH_CARD_SCROLL_AMOUNT) {
          // When near start, jump to corresponding position in second half
          container.scrollLeft = currentScroll + halfPoint;
        }
        container.scrollBy({
          left: -LAUNCH_CARD_SCROLL_AMOUNT,
          behavior: 'smooth'
        });
      }
    }
  }, []);

  // Auto-scroll functions
  const startAutoScroll = React.useCallback(() => {
    if (autoScrollIntervalRef.current) clearInterval(autoScrollIntervalRef.current);

    autoScrollIntervalRef.current = setInterval(() => {
      scrollLaunches('right');
    }, AUTO_SCROLL_INTERVAL_MS);
  }, [scrollLaunches]);

  const stopAutoScroll = React.useCallback(() => {
    if (autoScrollIntervalRef.current) {
      clearInterval(autoScrollIntervalRef.current);
      autoScrollIntervalRef.current = null;
    }
  }, []);

  // Check if launch carousel has overflow
  const checkLaunchOverflow = React.useCallback(() => {
    const container = launchCarouselRef.current;
    if (container) {
      const hasOverflow = container.scrollWidth > container.clientWidth;
      setShowLaunchScrollButtons(hasOverflow);
    }
  }, []);

  // Check overflow on window resize and scroll
  useEffect(() => {
    const handleResize = () => {
      checkTabsOverflow();
    };

    const handleScroll = () => {
      checkScrollButtonStates();
    };

    // Check overflow after component mounts and tabs are rendered
    const timer = setTimeout(checkTabsOverflow, 100);

    window.addEventListener('resize', handleResize);

    // Add scroll listener to the tabs container
    const container = tabsContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
    }

    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
      if (container) {
        container.removeEventListener('scroll', handleScroll);
      }
    };
  }, [activeTab, checkTabsOverflow, checkScrollButtonStates]); // Re-run when activeTab changes

  // Check launch carousel overflow on resize and mount
  useEffect(() => {
    const handleResize = () => {
      checkLaunchOverflow();
    };

    // Check overflow after launches are loaded
    const timer = setTimeout(() => {
      checkLaunchOverflow();
      // Start auto-scroll if we have launches
      if (upcomingLaunches.length > 0) {
        startAutoScroll();
      }
    }, 200);

    window.addEventListener('resize', handleResize);

    return () => {
      clearTimeout(timer);
      window.removeEventListener('resize', handleResize);
      // Clean up auto-scroll
      stopAutoScroll();
    };
  }, [upcomingLaunches, checkLaunchOverflow, startAutoScroll, stopAutoScroll]);

  return (
    <HelmetProvider>
      <Helmet>
        <title>T-0 Space News | Latest Space Exploration News & Rocket Launches</title>
        <meta name="description" content="Stay updated with the latest space exploration news, rocket launches, and cosmic discoveries. Real-time updates on SpaceX, NASA missions, and upcoming space events." />
        <meta name="keywords" content="space news, rocket launches, SpaceX, NASA, space exploration, satellites, space missions, astronomy, aerospace" />
        <link rel="canonical" href="https://t-minus-zero.vercel.app/" />
      </Helmet>

      <>
        {/* Fixed Space Background */}
        <div className="space-background"></div>

      {/* Main Content Overlay */}
      <div className="min-h-screen flex flex-col">
        <div className="space-overlay w-full min-h-screen flex flex-col">
          <header className="space-header text-white py-6 shadow">
            <div className="px-4 flex justify-between items-center">
              <h1 className="text-3xl font-bold">🚀 Space Launch News</h1>
              <div className="text-right">
                <div className="text-lg font-semibold">
                  {currentTime.toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                    hour12: true,
                  })}
                </div>
                <div className="text-sm opacity-90">📍 {location}</div>
              </div>
            </div>
          </header>

          {/* Tabs Section */}
          <div className="relative bg-gradient-to-r from-blue-900/50 to-purple-900/50 backdrop-blur-sm border-b border-blue-500/20">
            <div className="flex items-center">
              {/* Left Scroll Button - Only show if overflow */}
              {showScrollButtons && (
                <button
                  onClick={() => scrollTabs('left')}
                  disabled={!canScrollLeft}
                  className={`flex-shrink-0 p-2 rounded-l-lg transition-all duration-200 ${
                    canScrollLeft
                      ? 'text-white/70 hover:text-white hover:bg-white/10 cursor-pointer'
                      : 'text-white/30 cursor-not-allowed'
                  }`}
                  aria-label="Scroll tabs left"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
              )}

              {/* Tabs Container */}
              <div
                ref={tabsContainerRef}
                className="tabs-container flex overflow-x-auto px-2 py-3 space-x-1 flex-1"
                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
              >
                {spaceAgencies.map((agency) => (
                  <button
                    key={agency.id}
                    onClick={() => setActiveTab(agency.name)}
                    className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 whitespace-nowrap ${
                      activeTab === agency.name
                        ? 'bg-white text-blue-900 shadow-lg'
                        : 'text-white/80 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    {agency.name}
                  </button>
                ))}
              </div>

              {/* Right Scroll Button - Only show if overflow */}
              {showScrollButtons && (
                <button
                  onClick={() => scrollTabs('right')}
                  disabled={!canScrollRight}
                  className={`flex-shrink-0 p-2 rounded-r-lg transition-all duration-200 ${
                    canScrollRight
                      ? 'text-white/70 hover:text-white hover:bg-white/10 cursor-pointer'
                      : 'text-white/30 cursor-not-allowed'
                  }`}
                  aria-label="Scroll tabs right"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              )}
            </div>
          </div>

          {/* Launch Carousel Section */}
          {upcomingLaunches.length > 0 && (
            <div className="bg-gradient-to-r from-purple-900/15 to-blue-900/15 border-b border-purple-500/20">
              <div className="px-4 py-3">
                {/* Launch Cards Carousel with Side Controls */}
                <div className="relative flex items-center">
                  {/* Left Scroll Button */}
                  {showLaunchScrollButtons && (
                    <button
                      onClick={() => {
                        stopAutoScroll();
                        scrollLaunches('left');
                        setTimeout(startAutoScroll, AUTO_SCROLL_RESTART_DELAY_MS);
                      }}
                      className="absolute left-2 z-20 p-3 bg-black/50 hover:bg-black/70 text-white rounded-full transition-all duration-200 hover:scale-110 backdrop-blur-sm"
                      aria-label="Scroll launches left"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                      </svg>
                    </button>
                  )}

                  {/* Launch Cards Container */}
                  <div
                    ref={launchCarouselRef}
                    className="launch-carousel flex gap-4 overflow-x-auto pb-2 px-16 py-4"
                    style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
                    onMouseEnter={stopAutoScroll}
                    onMouseLeave={startAutoScroll}
                  >
                    {/* First set of launches */}
                    {upcomingLaunches.map((launch) => (
                      <LaunchCard
                        key={`first-${launch.id}`}
                        launch={launch}
                        onClick={() => setSelectedLaunch(launch)}
                      />
                    ))}

                    {/* Second set of launches for seamless looping */}
                    {upcomingLaunches.map((launch) => (
                      <LaunchCard
                        key={`second-${launch.id}`}
                        launch={launch}
                        onClick={() => setSelectedLaunch(launch)}
                      />
                    ))}
                  </div>

                  {/* Right Scroll Button */}
                  {showLaunchScrollButtons && (
                    <button
                      onClick={() => {
                        stopAutoScroll();
                        scrollLaunches('right');
                        setTimeout(startAutoScroll, AUTO_SCROLL_RESTART_DELAY_MS);
                      }}
                      className="absolute right-2 z-20 p-3 bg-black/50 hover:bg-black/70 text-white rounded-full transition-all duration-200 hover:scale-110 backdrop-blur-sm"
                      aria-label="Scroll launches right"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          <main className="flex-grow p-4 grid gap-3 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {articles.map((article) => (
              <article
                key={article.id}
                className="bg-white rounded-lg shadow hover:shadow-lg transition-all duration-300 overflow-hidden flex flex-col group relative cursor-pointer"
                onClick={() => setSelectedArticle(article)}
              >
                <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-75 transition-opacity duration-300 z-10 rounded-lg"></div>
                <div className="flex flex-col flex-grow relative z-20">
                  <img
                    src={article.image_url}
                    alt={article.title}
                    className="w-full h-48 object-cover"
                  />
                  <div className="p-4 flex flex-col flex-grow">
                    <h2 className="font-semibold text-lg mb-2 flex-grow group-hover:text-white transition-colors duration-300">
                      {article.title}
                    </h2>
                    <p className="text-gray-700 text-sm mb-3 line-clamp-3 group-hover:text-gray-200 transition-colors duration-300">
                      {article.summary}
                    </p>
                    <p className="text-gray-500 text-xs group-hover:text-gray-300 transition-colors duration-300">
                      {article.news_site || article.authors?.[0]?.name} ·{" "}
                      {dayjs(article.published_at).format("MMM D, YYYY")}
                    </p>
                  </div>
                </div>
              </article>
            ))}
          </main>

          <footer className="space-footer text-white py-4 text-center">
            <p>Powered by Space News Feed · {new Date().getFullYear()}</p>
          </footer>
        </div>
      </div>

      {/* Article Modal */}
      <Modal isOpen={!!selectedArticle} onClose={() => setSelectedArticle(null)}>
        {selectedArticle && (
          <>
            {/* Header Image */}
            <img
              src={selectedArticle.image_url}
              alt={selectedArticle.title}
              className="w-full h-64 object-cover rounded-lg mb-6"
            />

            {/* Article Info */}
            <div className="mb-4">
              <div className="flex items-center gap-2 text-sm text-gray-300 mb-2">
                <span className="font-medium text-gray-200">{selectedArticle.news_site || selectedArticle.authors?.[0]?.name}</span>
                <span>·</span>
                <span>{dayjs(selectedArticle.published_at).format("MMMM D, YYYY at h:mm A")}</span>
              </div>

              {/* Authors */}
              {selectedArticle.authors && selectedArticle.authors.length > 0 && (
                <div className="text-sm text-gray-300 mb-4">
                  By: {selectedArticle.authors.map(author => author.name).join(", ")}
                </div>
              )}
            </div>

            {/* Title */}
            <h1 className="text-3xl font-bold text-white mb-6">
              {selectedArticle.title}
            </h1>

            {/* Detailed News Content */}
            <div className="prose prose-lg max-w-none mb-6">
              {selectedArticle.detailed_news && selectedArticle.detailed_news.trim() !== "" ? (
                <div className="text-gray-200 leading-relaxed whitespace-pre-wrap">
                  {selectedArticle.detailed_news}
                </div>
              ) : selectedArticle.summary ? (
                <div className="text-gray-200 leading-relaxed">
                  {selectedArticle.summary}
                </div>
              ) : (
                <div className="text-gray-300 italic">
                  <p>Content is being processed. Please check back later for the complete article summary.</p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 pt-4 border-t border-gray-600">
              <a
                href={selectedArticle.url}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors duration-200 flex items-center gap-2"
              >
                Read Original Article
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
              <button
                onClick={() => setSelectedArticle(null)}
                className="bg-gray-700 text-gray-200 px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors duration-200"
              >
                Close
              </button>
            </div>
          </>
        )}
      </Modal>

      {/* Launch Modal */}
      <Modal isOpen={!!selectedLaunch} onClose={() => setSelectedLaunch(null)}>
        {selectedLaunch && (
          <>
            {/* Header Image */}
            <img
              src={selectedLaunch.image || "https://images.unsplash.com/photo-1517976487492-5750f3195933?w=800&h=400&fit=crop"}
              alt={selectedLaunch.name}
              className="w-full h-64 object-cover rounded-lg mb-6"
              onError={(e) => {
                e.target.src = "https://images.unsplash.com/photo-1517976487492-5750f3195933?w=800&h=400&fit=crop";
              }}
            />

            {/* Launch Info Header */}
            <div className="mb-4">
              <div className="flex items-center gap-2 text-sm text-gray-300 mb-2">
                <span className="font-medium text-gray-200">{selectedLaunch.lsp_name}</span>
                <span>·</span>
                <span>{dayjs(selectedLaunch.net).format("MMMM D, YYYY at h:mm A")} UTC</span>
                {selectedLaunch.status && (
                  <>
                    <span>·</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      selectedLaunch.status === 'Go' ? 'bg-green-600 text-white' :
                      selectedLaunch.status === 'TBD' ? 'bg-yellow-600 text-white' :
                      'bg-gray-600 text-white'
                    }`}>
                      {selectedLaunch.status}
                    </span>
                  </>
                )}
              </div>

              {/* Launch Window */}
              {selectedLaunch.window_start && selectedLaunch.window_end && (
                <div className="text-sm text-gray-300 mb-2">
                  Launch Window: {dayjs(selectedLaunch.window_start).format("h:mm A")} - {dayjs(selectedLaunch.window_end).format("h:mm A")} UTC
                </div>
              )}
            </div>

            {/* Title */}
            <h1 className="text-3xl font-bold text-white mb-6">
              {selectedLaunch.name}
            </h1>

            {/* Launch Details Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              {/* Mission Details */}
              <div className="bg-white/5 rounded-lg p-4">
                <h3 className="text-xl font-semibold text-white mb-3 flex items-center gap-2">
                  🚀 Mission Details
                </h3>
                <div className="space-y-2 text-gray-200">
                  <div><strong>Mission:</strong> {selectedLaunch.mission_name || 'Unknown'}</div>
                  {selectedLaunch.mission_type && (
                    <div><strong>Type:</strong> {selectedLaunch.mission_type}</div>
                  )}
                  {selectedLaunch.orbit && (
                    <div><strong>Target Orbit:</strong> {selectedLaunch.orbit}</div>
                  )}
                </div>
              </div>

              {/* Launch Site Details */}
              <div className="bg-white/5 rounded-lg p-4">
                <h3 className="text-xl font-semibold text-white mb-3 flex items-center gap-2">
                  📍 Launch Site
                </h3>
                <div className="space-y-2 text-gray-200">
                  <div><strong>Location:</strong> {selectedLaunch.location || 'Unknown'}</div>
                  {selectedLaunch.pad && (
                    <div><strong>Launch Pad:</strong> {selectedLaunch.pad}</div>
                  )}
                  {selectedLaunch.launch_site && selectedLaunch.launch_site !== selectedLaunch.location && (
                    <div><strong>Site:</strong> {selectedLaunch.launch_site}</div>
                  )}
                </div>
              </div>

              {/* Rocket Details */}
              <div className="bg-white/5 rounded-lg p-4">
                <h3 className="text-xl font-semibold text-white mb-3 flex items-center gap-2">
                  🚀 Rocket
                </h3>
                <div className="space-y-2 text-gray-200">
                  <div><strong>Vehicle:</strong> {selectedLaunch.rocket || 'Unknown'}</div>
                  {selectedLaunch.rocket_config_family && (
                    <div><strong>Family:</strong> {selectedLaunch.rocket_config_family}</div>
                  )}
                </div>
              </div>

              {/* Launch Provider */}
              <div className="bg-white/5 rounded-lg p-4">
                <h3 className="text-xl font-semibold text-white mb-3 flex items-center gap-2">
                  🏢 Launch Provider
                </h3>
                <div className="space-y-2 text-gray-200">
                  <div><strong>Company:</strong> {selectedLaunch.lsp_name || 'Unknown'}</div>
                  {selectedLaunch.lsp_type && (
                    <div><strong>Type:</strong> {selectedLaunch.lsp_type}</div>
                  )}
                  {selectedLaunch.lsp_country && (
                    <div><strong>Country:</strong> {selectedLaunch.lsp_country}</div>
                  )}
                </div>
              </div>
            </div>

            {/* Mission Description */}
            {selectedLaunch.mission_description && (
              <div className="mb-6">
                <h3 className="text-xl font-semibold text-white mb-3 flex items-center gap-2">
                  📋 Mission Description
                </h3>
                <div className="text-gray-200 leading-relaxed bg-white/5 rounded-lg p-4">
                  {selectedLaunch.ai_summary}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-4 pt-4 border-t border-gray-600">
              <button
                onClick={() => setSelectedLaunch(null)}
                className="bg-gray-700 text-gray-200 px-6 py-2 rounded-lg hover:bg-gray-600 transition-colors duration-200"
              >
                Close
              </button>
            </div>
          </>
        )}
      </Modal>
      </>
    </HelmetProvider>
  );
}

export default App;
