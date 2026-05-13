FROM denoland/deno:2.7.14 AS builder
WORKDIR /app
COPY deno.json deno.lock* ./
RUN deno install
COPY . .
RUN deno task build

FROM denoland/deno:2.7.14
WORKDIR /app
COPY --from=builder /app/_fresh ./_fresh
COPY --from=builder /app/deno.json ./
COPY --from=builder /app/static ./static
COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]