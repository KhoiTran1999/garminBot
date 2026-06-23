export default {
    async fetch(request, env, ctx) {
        if (request.method !== "POST") {
            return new Response("Method not allowed", { status: 405 });
        }
        
        let mode = "";
        let targetRepo = "";
    }
}
