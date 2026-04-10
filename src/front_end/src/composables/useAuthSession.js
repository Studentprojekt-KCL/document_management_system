import { onMounted, onUnmounted } from "vue"
import router from "@/router"
import { refreshToken, logout, getAccessToken, isTokenExpired} from "@/utils/auth.js"

export function useAuthSession(){
    let lastActivity = Date.now()
    let lastRefresh = Date.now()
    let intervalID = null

    // configuration
    const TIME_LIMIT = 2*60*1000 //30 minutes
    const REFRESH_TIME = 1*60*1000 // 25 minutes

    // update functions for lastActivity
    const updateActivity = ()=>{
        console.log("activty detected") // remove after testing
        lastActivity = Date.now()
    }
    const triggerLogout = () => {
        console.log("rigger loggout() called - logging out user")
        logout()
        router.push('/')
    }
    // Synchronize logout across multiple tabs for storage events.
    const syncLogout = (event) => {
        if (event.key === 'logout-event') {
            sessionStorage.clear()
            router.push('/')
        }
    }

    const activity_loop = () => {
        console.log("auth loop started") // remove after testing
        intervalID = setInterval(async () => {
            console.log("checking session...") // remove after testing
            const now = Date.now()
            const isActive = (now - lastActivity) < TIME_LIMIT
            console.log({
                isActive,
                timeSinceActivity: now -lastActivity
            })
            if (!isActive){
                console.log("inactive -> logging out")
                triggerLogout()
                return
            }
            const token = getAccessToken()

            if (!token){
                console.log("no token")
                triggerLogout()
                return
            }

            try {
                if (isTokenExpired(token)){
                    console.log("refreshing token now...") // remove after testing
                    await refreshToken()
                    lastRefresh = now
                    return
                }

                const shouldRefresh = (now - lastRefresh) > REFRESH_TIME
                if(shouldRefresh){
                    console.log("active- should refresh...")
                    await refreshToken()
                    lastRefresh = now
                }
            }
            catch(err){
                console.error("refresh failed:", err)
            }
            
        } , 60 * 1000)
    }
    // life cycle
    onMounted(()=> {
        window.addEventListener('mousemove', updateActivity)
        window.addEventListener('keydown', updateActivity)
        window.addEventListener('click', updateActivity)
        window.addEventListener('scroll', updateActivity)
        window.addEventListener('storage', syncLogout)
        
        activity_loop()
    })
    onUnmounted(()=>{
        window.removeEventListener('mousemove', updateActivity)
        window.removeEventListener('keydown', updateActivity)
        window.removeEventListener('click', updateActivity)
        window.removeEventListener('scroll', updateActivity)
        window.removeEventListener('storage', syncLogout)
        clearInterval(intervalID)
    })
}
