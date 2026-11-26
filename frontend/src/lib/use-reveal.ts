import { useEffect, useRef, useState } from 'react'

/**
 * Vrai dès que l'élément entre à l'écran, une seule fois. Sans IntersectionObserver
 * (navigateur ancien, tests), l'élément est montré tout de suite : rien ne reste caché.
 */
export function useInView<T extends Element>(margin = '0px 0px -12% 0px') {
  const ref = useRef<T>(null)
  const [shown, setShown] = useState(() => typeof IntersectionObserver === 'undefined')
  useEffect(() => {
    const element = ref.current
    if (element === null || typeof IntersectionObserver === 'undefined') return
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setShown(true)
          observer.disconnect()
        }
      },
      { rootMargin: margin },
    )
    observer.observe(element)
    return () => observer.disconnect()
  }, [margin])
  return { ref, shown }
}
