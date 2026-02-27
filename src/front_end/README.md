# Vue 3 + Vite

This template should help get you started developing with Vue 3 in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about IDE Support for Vue in the [Vue Docs Scaling up Guide](https://vuejs.org/guide/scaling-up/tooling.html#ide-support).

# Build Instructions
docker build -t test_frontend .

# Run instructions after build
docker run --rm -d --name test_frontend_run -p 8080:80 test_frontend

# Open a browers and enter localhost
localhost:8080

# To stop docker
docker stop test_frontend_run

# see live changes

# install npm
npm install

# run npm
npm run dev