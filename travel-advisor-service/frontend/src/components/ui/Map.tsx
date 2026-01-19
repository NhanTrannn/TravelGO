"use client"

import React from 'react'
import { GoogleMap, Marker, useLoadScript } from '@react-google-maps/api'

interface MapProps {
  center: {
    lat: number
    lng: number
  }
  zoom?: number
  height?: number | string
}

const Map: React.FC<MapProps> = ({ center, zoom = 15, height = 400 }) => {
  const { isLoaded } = useLoadScript({
    googleMapsApiKey: process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY || "",
  })

  if (!isLoaded) return <div>Đang tải bản đồ...</div>

  return (
    <GoogleMap
      mapContainerStyle={{ width: '100%', height, borderRadius: '0.5rem' }}
      center={center}
      zoom={zoom}
    >
      <Marker position={center} />
    </GoogleMap>
  )
}

export default Map
