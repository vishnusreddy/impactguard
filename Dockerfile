FROM node:22-slim AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY frontend ./frontend
COPY vite.config.js ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements-cloud.txt ./requirements-cloud.txt
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY backend ./backend
COPY --from=frontend /app/dist ./dist
RUN useradd --create-home app && mkdir /app/.data && chown -R app:app /app
USER app
ENV PORT=8080 HOST=0.0.0.0
EXPOSE 8080
CMD ["python", "backend/server.py"]
