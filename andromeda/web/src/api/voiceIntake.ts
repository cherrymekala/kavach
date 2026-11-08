import { useCallback, useEffect, useRef, useState } from 'react'
import { Player, Recorder } from '@/audio/audio'
import { getIdToken } from '@/firebase'
import type { Document } from './types'

/** Protocol: sombrero/src/kavach/routers/voice_intake.py (module docstring). */

export type VoiceLine = { id: number; who: 'ai' | 'you'; text: string }
export type VoiceState = 'idle' | 'connecting' | 'live' | 'ending' | 'saved' | 'error'

const WS_URL = (import.meta.env.VITE_API_URL ?? '').replace(/^http/, 'ws')

/**
 * Voice-first intake: the patient tells what happened, in their language, and the transcript
 * is saved to the case as a document. Same audio pipeline as the hearing rehearsal.
 */
export function useVoiceIntake(caseId: string | undefined) {
  const [state, setState] = useState<VoiceState>('idle')
  const [lines, setLines] = useState<VoiceLine[]>([])
  const [yourTurn, setYourTurn] = useState(false)
  const [micOn, setMicOn] = useState(false)
  const [saved, setSaved] = useState<Document | null>(null)
  const [error, setError] = useState<string | null>(null)

  const ws = useRef<WebSocket | null>(null)
  const player = useRef<Player | null>(null)
  const recorder = useRef<Recorder | null>(null)
  const nextId = useRef(0)

  const add = useCallback((who: 'ai' | 'you', text: string) => {
    setLines((list) => {
      const last = list[list.length - 1]
      // Transcripts arrive in small chunks: keep extending the current speaker's line.
      if (last && last.who === who) return [...list.slice(0, -1), { ...last, text: last.text + text }]
      nextId.current += 1
      return [...list, { id: nextId.current, who, text: text.trimStart() }]
    })
  }, [])

  const stopMic = useCallback(() => {
    recorder.current?.stop()
    recorder.current = null
    setMicOn(false)
  }, [])

  const cleanup = useCallback(() => {
    stopMic()
    player.current?.close()
    player.current = null
    ws.current?.close()
    ws.current = null
  }, [stopMic])

  useEffect(() => cleanup, [cleanup])

  const send = (msg: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(msg))
  }

  const toggleMic = useCallback(async () => {
    if (recorder.current) return stopMic()
    try {
      const r = new Recorder()
      await r.start((audio) => send({ audio }))
      recorder.current = r
      setMicOn(true)
    } catch {
      setError('mic')
    }
  }, [stopMic])

  const start = useCallback(async () => {
    if (!caseId) return
    setLines([])
    setSaved(null)
    setError(null)
    setState('connecting')
    player.current = new Player()
    await player.current.resume()
    const token = await getIdToken()
    const socket = new WebSocket(`${WS_URL}/cases/${caseId}/voice-intake`)
    ws.current = socket
    socket.onopen = () => {
      socket.send(JSON.stringify({ token }))
      setState('live')
    }
    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data as string)
      if (msg.audio) player.current?.play(msg.audio)
      else if (msg.transcript) {
        if (msg.transcript.who === 'you') {
          player.current?.interrupt()
          setYourTurn(false)
        }
        add(msg.transcript.who, msg.transcript.text)
      } else if (msg.turn_complete) setYourTurn(true)
      else if ('saved' in msg) {
        setSaved(msg.saved?.document ?? null)
        setState('saved')
        stopMic()
      } else if (msg.error) {
        setError(msg.error)
        setState('error')
      }
    }
    socket.onerror = () => {
      setError('dropped')
      setState('error')
    }
    socket.onclose = () => {
      stopMic()
      setState((s) => (s === 'live' || s === 'connecting' ? 'error' : s))
    }
  }, [caseId, add, stopMic])

  const sendText = useCallback(
    (text: string) => {
      const clean = text.trim()
      if (!clean) return
      player.current?.interrupt()
      add('you', clean)
      setYourTurn(false)
      send({ text: clean })
    },
    [add],
  )

  const end = useCallback(() => {
    setState('ending')
    stopMic()
    send({ end: true })
  }, [stopMic])

  return { state, lines, yourTurn, micOn, saved, error, start, toggleMic, sendText, end, cleanup }
}
