FROM node:22.23.1-bookworm-slim

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /workspace/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
