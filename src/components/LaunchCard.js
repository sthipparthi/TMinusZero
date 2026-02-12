import React from "react";
import dayjs from "dayjs";

const FALLBACK_IMAGE = "https://images.unsplash.com/photo-1517976487492-5750f3195933?w=400&h=200&fit=crop";

function LaunchCard({ launch, onClick }) {
  return (
    <div
      className="flex-shrink-0 w-40 bg-white/10 rounded-lg p-2 border border-white/20 hover:border-white/40 transition-all duration-300 hover:transform hover:scale-105 hover:shadow-2xl hover:shadow-black/50 cursor-pointer"
      onClick={onClick}
    >
      {/* Launch Image */}
      {launch.image && (
        <img
          src={launch.image}
          alt={launch.name}
          className="w-full h-20 object-cover rounded-lg mb-2"
          onError={(e) => {
            e.target.src = FALLBACK_IMAGE;
          }}
        />
      )}

      {/* Launch Info */}
      <div className="text-white">
        <h3 className="font-semibold text-sm mb-2 line-clamp-2">
          {launch.name}
        </h3>

        <div className="space-y-1 text-xs text-gray-300">
          <div className="flex items-center gap-1">
            <span className="font-medium">📅</span>
            <span>{dayjs(launch.window_start).format("MMM D, YYYY")}</span>
          </div>

          {launch.location && (
            <div className="flex items-center gap-1">
              <span className="font-medium">📍</span>
              <span className="line-clamp-1 text-xs">{launch.location}</span>
            </div>
          )}

          {launch.lsp_name && (
            <div className="flex items-center gap-1">
              <span className="font-medium">🏢</span>
              <span className="line-clamp-1 text-xs">{launch.lsp_name}</span>
            </div>
          )}

          {(launch.mission_name || launch.mission) && (launch.mission_name || launch.mission) !== "Unknown Payload" && (
            <div className="flex items-center gap-1">
              <span className="font-medium">🚀</span>
              <span className="line-clamp-1 text-xs">{launch.mission_name || launch.mission}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default React.memo(LaunchCard);
