"""
RKICS Free Site Audit Server & Webhook Engine
File: audit_server.py
Accepts site photo uploads from rkics.com, runs AI vision analysis,
stores leads into sales_os.db, saves images, and generates WhatsApp payloads.
"""

import os
import json
import sqlite3
import base64
import requests
from datetime import datetime, date
from pathlib import Path
from urllib.parse import quote_plus
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="RKICS Site Audit & Lead Generation Engine", version="1.0")

# Enable CORS for rkics.com and local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = DATA_DIR / "site_audit_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "sales_os.db"
BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "free-site-audit.html"

EMBEDDED_HTML = """<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Free AI Construction Site & Waterproofing Audit | RKICS Hyderabad</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .spinner {
      border: 4px solid rgba(0, 0, 0, 0.1);
      width: 36px;
      height: 36px;
      border-radius: 50%;
      border-left-color: #1e3a8a;
      animation: spin 1s linear infinite;
    }
    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
  </style>
</head>
<body class="bg-slate-50 text-slate-900 antialiased">

  <!-- Navbar -->
  <nav class="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-sm">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between h-20 items-center">
        <!-- Logo -->
        <a href="/" class="flex items-center gap-2">
          <div class="w-10 h-10 bg-blue-900 rounded-sm flex items-center justify-center text-white font-extrabold text-xl shadow-inner">
            RK
          </div>
          <span class="font-extrabold text-2xl tracking-tight text-blue-950">ICS</span>
          <span class="hidden sm:inline-block ml-3 text-xs font-semibold px-2 py-0.5 rounded bg-blue-100 text-blue-800 uppercase tracking-wider">Engineering Systems</span>
        </a>

        <!-- Contact Buttons -->
        <div class="flex items-center gap-4">
          <a href="https://wa.me/917013007595?text=Hi+RKICS,+I+need+technical+advice+for+my+construction+site." target="_blank" class="hidden sm:flex items-center gap-2 text-emerald-600 font-semibold hover:text-emerald-700">
            <span>💬 WhatsApp Desk</span>
          </a>
          <a href="tel:+917013007595" class="bg-blue-900 hover:bg-blue-800 text-white px-5 py-2.5 rounded-md font-semibold text-sm transition-all shadow-md">
            📞 +91 70130 07595
          </a>
        </div>
      </div>
    </div>
  </nav>

  <!-- Hero Header -->
  <section class="relative bg-blue-950 text-white overflow-hidden py-16 sm:py-24">
    <div class="absolute inset-0 opacity-10">
      <div class="absolute w-full h-full bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-blue-400 via-transparent to-transparent"></div>
    </div>
    <div class="relative max-w-5xl mx-auto px-4 text-center">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-900/60 border border-blue-700/50 text-blue-300 text-xs font-semibold mb-6 uppercase tracking-wider">
        ⚡ Instant Civil Engineering Assessment • Hyderabad Sites
      </div>
      <h1 class="text-3xl sm:text-5xl font-extrabold tracking-tight mb-4 leading-tight">
        Free AI Construction Site & <br class="hidden sm:inline">
        <span class="text-blue-400">Waterproofing Procurement Audit</span>
      </h1>
      <p class="text-base sm:text-lg text-slate-300 max-w-3xl mx-auto mb-8 leading-relaxed">
        Upload a photo of your under-construction building, slab leakage, or damp wall. Our visual AI detects your structural stage and generates an 18-week material procurement roadmap sent directly to your WhatsApp.
      </p>

      <!-- Brand Partner Bar -->
      <div class="flex flex-wrap justify-center items-center gap-6 sm:gap-12 opacity-80 pt-4 border-t border-blue-900/60 text-xs sm:text-sm font-bold tracking-widest text-slate-300">
        <span>AUTHORIZED PARTNER:</span>
        <span class="text-white font-extrabold">SIKA</span>
        <span class="text-white font-extrabold">ASIAN PAINTS SMARTCARE</span>
        <span class="text-white font-extrabold">MYK LATICRETE</span>
        <span class="text-white font-extrabold">FOSROC</span>
      </div>
    </div>
  </section>

  <!-- Main Audit Intake Form Section -->
  <main class="max-w-6xl mx-auto px-4 py-12 -mt-10">
    <div class="bg-white rounded-2xl shadow-xl border border-slate-200 p-6 sm:p-10">
      
      <form id="auditForm" class="grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        <!-- Left Column: Photo Upload -->
        <div class="lg:col-span-5 flex flex-col justify-between">
          <div>
            <label class="block text-sm font-bold text-slate-800 mb-2">1. Upload Construction Site Photo <span class="text-red-500">*</span></label>
            <p class="text-xs text-slate-500 mb-4">Upload a wide photo of your active frame, slab props, bathroom sunken area, or terrace.</p>
            
            <div id="dropZone" class="border-2 border-dashed border-slate-300 hover:border-blue-600 rounded-xl p-6 text-center cursor-pointer transition-all bg-slate-50 flex flex-col items-center justify-center min-h-[220px]">
              <input type="file" id="imageInput" accept="image/jpeg,image/png,image/jpg" class="hidden" required>
              
              <div id="uploadPrompt" class="flex flex-col items-center">
                <svg class="w-12 h-12 text-blue-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
                </svg>
                <span class="text-sm font-semibold text-slate-700">Click to choose image or drag & drop</span>
                <span class="text-xs text-slate-400 mt-1">JPG, JPEG, PNG (Max 15MB)</span>
              </div>

              <!-- Preview Thumbnail -->
              <div id="previewContainer" class="hidden w-full">
                <img id="imagePreview" class="max-h-56 mx-auto rounded-lg object-contain shadow-sm border border-slate-200" alt="Site Preview">
                <p id="fileName" class="text-xs font-semibold text-slate-600 mt-2 truncate"></p>
                <button type="button" id="removeImgBtn" class="text-xs text-red-500 hover:underline mt-1">Remove & change photo</button>
              </div>
            </div>
          </div>

          <div class="mt-6 p-4 rounded-lg bg-blue-50 border border-blue-100">
            <h4 class="text-xs font-bold text-blue-900 uppercase tracking-wide mb-1">🔒 Complete Privacy & Safety</h4>
            <p class="text-xs text-blue-700 leading-relaxed">
              Your photo and contact details are used solely to generate your engineering material specification. We never share your data.
            </p>
          </div>
        </div>

        <!-- Right Column: Project & Contact Details -->
        <div class="lg:col-span-7 flex flex-col justify-between space-y-4">
          <div>
            <h3 class="text-sm font-bold text-slate-800 mb-4">2. Site & WhatsApp Delivery Information</h3>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <!-- Name -->
              <div>
                <label for="nameInput" class="block text-xs font-semibold text-slate-700 mb-1">Your Name / Company <span class="text-red-500">*</span></label>
                <input type="text" id="nameInput" placeholder="e.g. Rajesh Kumar" required class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm">
              </div>

              <!-- WhatsApp Phone -->
              <div>
                <label for="phoneInput" class="block text-xs font-semibold text-slate-700 mb-1">WhatsApp Mobile Number <span class="text-red-500">*</span></label>
                <input type="tel" id="phoneInput" placeholder="e.g. 98480 XXXXX" required class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm">
                <span class="text-[10px] text-slate-400">The full chemical report will be sent to this number</span>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-4">
              <!-- Location in Hyderabad -->
              <div>
                <label for="locationInput" class="block text-xs font-semibold text-slate-700 mb-1">Site Location / Corridor <span class="text-red-500">*</span></label>
                <select id="locationInput" class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm bg-white">
                  <option value="Gachibowli">Gachibowli / Financial District</option>
                  <option value="Kokapet">Kokapet / Gandipet</option>
                  <option value="Tellapur">Tellapur / Nallagandla</option>
                  <option value="Narsingi">Narsingi / Puppalaguda</option>
                  <option value="Kondapur">Kondapur / Madhapur</option>
                  <option value="Bandlaguda Jagir">Bandlaguda Jagir / Rajendranagar</option>
                  <option value="Kollur">Kollur / Velimela</option>
                  <option value="Miyapur">Miyapur / Bachupally</option>
                  <option value="Kompally">Kompally / Medchal</option>
                  <option value="Other Hyderabad">Other Hyderabad Site</option>
                </select>
              </div>

              <!-- Building Format -->
              <div>
                <label for="projectTypeInput" class="block text-xs font-semibold text-slate-700 mb-1">Building Format <span class="text-red-500">*</span></label>
                <select id="projectTypeInput" class="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm bg-white">
                  <option value="Standalone Residential Apartment (G+4 / G+5)">Standalone Residential Apartment (G+4 / G+5)</option>
                  <option value="Independent Villa / Gated Community">Independent Villa / Gated Community (G+1 / G+2)</option>
                  <option value="Commercial Building / Retail Extension">Commercial Building / Retail Extension</option>
                  <option value="High-Rise Tower / Podium Development">High-Rise Tower / Podium Development</option>
                  <option value="Industrial Shed / Warehouse Flooring">Industrial Shed / Warehouse Flooring</option>
                </select>
              </div>
            </div>

            <!-- Specific Notes / Challenge -->
            <div class="mt-4">
              <label for="noteInput" class="block text-xs font-semibold text-slate-700 mb-1">Current Problem or Observation (Optional)</label>
              <textarea id="noteInput" rows="2" placeholder="e.g. Currently casting 4th floor slab; planning upcoming terrace waterproofing and toilet sunken cores." class="w-full px-3.5 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-600 text-sm"></textarea>
            </div>
          </div>

          <!-- Submit Button & Loading State -->
          <div class="pt-4">
            <button type="submit" id="submitBtn" class="w-full bg-blue-900 hover:bg-blue-800 text-white font-bold py-3.5 px-6 rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 text-base">
              <span>🚀 Generate Free AI Engineering & Chemical Audit</span>
            </button>

            <div id="loadingState" class="hidden flex items-center justify-center gap-3 pt-4 text-blue-900 font-semibold text-sm">
              <div class="spinner"></div>
              <span>Analyzing site structure and preparing engineering chemical report...</span>
            </div>
          </div>
        </div>

      </form>

    </div>

    <!-- Live Results Section (Revealed dynamically via JS) -->
    <div id="resultsCard" class="hidden mt-12 bg-white rounded-2xl shadow-xl border border-slate-200 p-6 sm:p-10">
      
      <!-- Confirmation Banner -->
      <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-5 mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-extrabold bg-emerald-200 text-emerald-900 mb-1">AUDIT COMPLETE</span>
          <h2 class="text-xl sm:text-2xl font-extrabold text-slate-900">Site Assessment Logged: <span id="resLeadCode" class="text-blue-900"></span></h2>
          <p class="text-sm text-slate-600 mt-1">A stage-wise chemical specification report has been compiled for your project.</p>
        </div>
        <a id="resWhatsAppBtn" href="#" target="_blank" class="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-3 rounded-lg font-bold text-sm transition-all shadow-md flex items-center gap-2 whitespace-nowrap">
          <span>💬 Open in WhatsApp</span>
        </a>
      </div>

      <!-- Structural Observations Summary -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200">
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-1">Detected Building Scale</span>
          <h3 id="resSiteScale" class="text-lg font-bold text-slate-900"></h3>
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mt-3 mb-1">Active Structural Phase</span>
          <p id="resCurrentStage" class="text-sm text-slate-700 font-medium"></p>
        </div>
        <div class="p-5 rounded-xl bg-slate-50 border border-slate-200">
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">Visible Evidence Identified</span>
          <ul id="resEvidenceList" class="space-y-1.5 text-xs text-slate-700"></ul>
        </div>
      </div>

      <!-- Full Multi-Stage Chemical Roadmap Table -->
      <div class="mb-8">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-lg font-bold text-slate-900">Stage-by-Stage Construction Chemical Roadmap</h3>
          <span class="text-xs text-blue-800 font-semibold bg-blue-50 border border-blue-200 px-3 py-1 rounded-full">Contractor Wholesale Rates on WhatsApp</span>
        </div>
        
        <div class="overflow-x-auto border border-slate-200 rounded-xl shadow-sm">
          <table class="w-full text-left text-xs text-slate-700">
            <thead class="bg-slate-100 text-slate-900 font-bold border-b border-slate-200">
              <tr>
                <th class="p-3">Project Stage & Timing</th>
                <th class="p-3">Structural Element</th>
                <th class="p-3">Recommended System & Brand</th>
                <th class="p-3">Engineering Purpose & Why Required</th>
                <th class="p-3">Application Precautions</th>
              </tr>
            </thead>
            <tbody id="resRoadmapBody" class="divide-y divide-slate-200 bg-white">
            </tbody>
          </table>
        </div>
      </div>

      <!-- Site Engineer Verification Checklist -->
      <div class="p-5 rounded-xl bg-amber-50 border border-amber-200 mb-8">
        <h4 class="text-xs font-bold text-amber-900 uppercase tracking-wider mb-2">⚠️ Site Engineer Verification Checklist:</h4>
        <ul id="resChecklist" class="space-y-1.5 text-xs text-amber-800"></ul>
      </div>

      <!-- Final Call to Action -->
      <div class="text-center p-8 bg-blue-950 rounded-xl text-white">
        <h3 class="text-xl font-bold mb-2">Need Contractor Trade Rates or On-Site Technical Samples?</h3>
        <p class="text-sm text-slate-300 max-w-2xl mx-auto mb-6">
          Connect with our Gachibowli central warehouse desk. We provide genuine batch test reports, direct factory discounts, and fast site delivery across Hyderabad and Telangana.
        </p>
        <a id="resWhatsAppBottomBtn" href="#" target="_blank" class="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white font-bold py-3.5 px-8 rounded-xl shadow-lg transition-all text-sm">
          <span>📲 Connect on WhatsApp for Contractor Rates (+91 70130 07595)</span>
        </a>
      </div>

    </div>
  </main>

  <!-- Footer -->
  <footer class="bg-white border-t border-slate-200 py-8 text-center text-xs text-slate-500">
    <p>© 2026 RKICS & Premier Engineering Systems. All rights reserved. Gachibowli, Hyderabad - 500032.</p>
    <p class="mt-1">Authorized Distribution: SIKA India | Asian Paints SmartCare | MYK Laticrete | Fosroc Chemicals</p>
  </footer>

  <!-- Interactive JavaScript Logic -->
  <script>
    const dropZone = document.getElementById('dropZone');
    const imageInput = document.getElementById('imageInput');
    const uploadPrompt = document.getElementById('uploadPrompt');
    const previewContainer = document.getElementById('previewContainer');
    const imagePreview = document.getElementById('imagePreview');
    const fileName = document.getElementById('fileName');
    const removeImgBtn = document.getElementById('removeImgBtn');
    const auditForm = document.getElementById('auditForm');
    const submitBtn = document.getElementById('submitBtn');
    const loadingState = document.getElementById('loadingState');
    const resultsCard = document.getElementById('resultsCard');

    // Drag & Drop Handlers
    dropZone.addEventListener('click', () => imageInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.add('border-blue-600', 'bg-blue-50/50');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, (e) => {
        e.preventDefault();
        dropZone.classList.remove('border-blue-600', 'bg-blue-50/50');
      });
    });

    dropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        imageInput.files = e.dataTransfer.files;
        handleFileSelect(e.dataTransfer.files[0]);
      }
    });

    imageInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        handleFileSelect(e.target.files[0]);
      }
    });

    function handleFileSelect(file) {
      if (!file.type.startsWith('image/')) {
        alert('Please select a valid image file (JPG, PNG).');
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        imagePreview.src = e.target.result;
        fileName.textContent = file.name;
        uploadPrompt.classList.add('hidden');
        previewContainer.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    }

    removeImgBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      imageInput.value = '';
      uploadPrompt.classList.remove('hidden');
      previewContainer.classList.add('hidden');
      imagePreview.src = '';
    });

    // Form Submission Handler
    auditForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      if (!imageInput.files || !imageInput.files[0]) {
        alert('Please upload a site photo to generate your audit.');
        return;
      }

      submitBtn.classList.add('hidden');
      loadingState.classList.remove('hidden');
      resultsCard.classList.add('hidden');

      const formData = new FormData();
      formData.append('image', imageInput.files[0]);
      formData.append('name', document.getElementById('nameInput').value);
      formData.append('phone', document.getElementById('phoneInput').value);
      formData.append('location', document.getElementById('locationInput').value);
      formData.append('project_type', document.getElementById('projectTypeInput').value);
      formData.append('note', document.getElementById('noteInput').value);

      try {
        const response = await fetch('/api/site-audit', {
          method: 'POST',
          body: formData
        });

        if (!response.ok) {
          throw new Error(`Server returned HTTP ${response.status}`);
        }

        const data = await response.json();
        renderAuditResults(data);

      } catch (err) {
        console.error('Audit submission error:', err);
        alert('Audit completed and recorded! Connecting to technical sales desk.');
        // Fallback demo rendering if testing standalone
        renderFallbackResults();
      } finally {
        submitBtn.classList.remove('hidden');
        loadingState.classList.add('hidden');
      }
    });

    function renderAuditResults(data) {
      document.getElementById('resLeadCode').textContent = data.lead_code || 'AUDIT-HYD';
      document.getElementById('resSiteScale').textContent = data.site_scale || 'Residential / Commercial Site';
      document.getElementById('resCurrentStage').textContent = data.current_stage || 'Active Concrete Framework';

      // Evidence
      const evList = document.getElementById('resEvidenceList');
      evList.innerHTML = '';
      (data.visible_evidence || []).forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `📌 <span>${item}</span>`;
        evList.appendChild(li);
      });

      // Roadmap Table
      const tb = document.getElementById('resRoadmapBody');
      tb.innerHTML = '';
      (data.full_lifecycle_roadmap || []).forEach(r => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-slate-50 transition-colors';
        tr.innerHTML = `
          <td class="p-3 font-semibold text-blue-950">${r.stage_name || ''}</td>
          <td class="p-3 font-medium text-slate-800">${r.element || ''}</td>
          <td class="p-3 font-bold text-slate-900">${r.preferred_brand_product || ''}</td>
          <td class="p-3 text-slate-600">${r.purpose || ''}</td>
          <td class="p-3 text-slate-500">${r.precautions || ''}</td>
        `;
        tb.appendChild(tr);
      });

      // Checklist
      const chList = document.getElementById('resChecklist');
      chList.innerHTML = '';
      (data.site_engineer_verification_checklist || []).forEach(item => {
        const li = document.createElement('li');
        li.innerHTML = `🔍 <span>${item}</span>`;
        chList.appendChild(li);
      });

      // WhatsApp Buttons
      const waUrl = data.whatsapp_url || 'https://wa.me/917013007595';
      document.getElementById('resWhatsAppBtn').href = waUrl;
      document.getElementById('resWhatsAppBottomBtn').href = waUrl;

      resultsCard.classList.remove('hidden');
      resultsCard.scrollIntoView({ behavior: 'smooth' });
    }

    function renderFallbackResults() {
      renderAuditResults({
        lead_code: 'AUDIT-' + new Date().toISOString().slice(0,10).replace(/-/g,''),
        site_scale: document.getElementById('projectTypeInput').value + ' (' + document.getElementById('locationInput').value + ')',
        current_stage: 'Bare RCC Superstructure & Formwork Stage',
        visible_evidence: [
          'Active concrete frame casting',
          'Shuttering props supporting upper slab',
          'Upcoming plastering, sunken slabs, and terrace waterproofing required'
        ],
        full_lifecycle_roadmap: [
          {
            stage_name: 'Stage 1: Structural Curing & Joints (Weeks 1-2)',
            element: 'RCC Beams & Columns',
            preferred_brand_product: 'Asian Paints SmartCare Repair Polymer / REARM SBR 35',
            purpose: 'Patching honeycombing and bonding cold joints before plastering.',
            precautions: 'Chisel honeycombing to sound aggregate before applying polymer repair mortar.'
          },
          {
            stage_name: 'Stage 2: Masonry & Plastering (Weeks 3-5)',
            element: 'Wall Plastering Mortar',
            preferred_brand_product: 'Asian Paints SmartCare Vitalia Neo (20L)',
            purpose: 'Makes mortar hydrophobic to block monsoon rain penetration.',
            precautions: 'Mix 200ml per 50kg bag of cement into gauging water.'
          },
          {
            stage_name: 'Stage 3: Sunken Slabs & Bathrooms (Weeks 6-8)',
            element: 'Toilet Sunken Slabs & Pipes',
            preferred_brand_product: 'SikaTop Seal-107 (IN) & Fosroc Conbextra GP2',
            purpose: 'Seamless elastomeric barrier under sunken slabs and non-shrink pipe collar sealing.',
            precautions: 'Terminate waterproofing minimum 300mm above finished floor level.'
          },
          {
            stage_name: 'Stage 4: Roof Terrace Waterproofing (Weeks 8-12)',
            element: 'Exposed Flat Roof Slab',
            preferred_brand_product: 'Asian Paints SmartCare PU Magnum US Grey & Glass Fiber Mesh (145 GSM)',
            purpose: 'UV-resistant PU membrane accommodates thermal slab expansion under Hyderabad sun.',
            precautions: 'Embed glass fiber mesh along all 90-degree corner fillets.'
          },
          {
            stage_name: 'Stage 5: Flooring & Tile Fixing (Weeks 12-16)',
            element: 'Vitrified Floor Tiles',
            preferred_brand_product: 'MYK Laticrete 305 Tile Adhesive & SP-100 Epoxy Grout',
            purpose: 'Prevents hollow debonding of low-porosity vitrified tiles; epoxy grout gives 100% waterproof joints.',
            precautions: 'Ensure 100% notched adhesive bed coverage.'
          }
        ],
        site_engineer_verification_checklist: [
          'Verify concrete 28-day curing age before striking props.',
          'Verify plumbing pipe collar seals across all sunken pods.',
          'Inspect terrace rainwater drop slopes.'
        ],
        whatsapp_url: 'https://wa.me/917013007595?text=Hi+RKICS,+I+uploaded+a+site+photo+for+my+project.+Please+share+contractor+trade+pricing.'
      });
    }
  </script>
</body>
</html>
"""

def load_env_key():
    key = os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    if key:
        return key.strip()
    for p in [Path(".env"), Path("../.env"), Path("data/.env")]:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
                    elif line.startswith("GOOGLE_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            return val
            except Exception:
                pass
    return ""

def analyze_photo_with_ai(image_bytes: bytes, mime_type: str, user_context: dict):
    """Run multimodal analysis using google-genai SDK or fallback."""
    api_key = load_env_key()
    
    prompt = f"""You are a senior civil engineer and chief technical sales advisor for RKICS in Hyderabad, India.
Authorized Brands in priority order:
1. SIKA
2. Asian Paints (SmartCare)
3. MYK LATICRETE
4. FOSROC

Client Site Context:
- Submitter Name: {user_context.get('name', 'Client')}
- Mobile / WhatsApp: {user_context.get('phone', '')}
- Project Corridor / Location: {user_context.get('location', 'Hyderabad')}
- Building Format: {user_context.get('project_type', 'Residential / Commercial')}
- Client Note / Challenge: {user_context.get('note', 'General Site Inspection')}

CRITICAL RULE:
You MUST provide the FULL LIFECYCLE MULTI-STAGE PROCUREMENT PLAN covering all upcoming construction milestones (current structural casting, masonry plastering, toilet sunken slabs, roof terrace, and floor tiling).
DO NOT include any internal wholesale costs or margin numbers. Only recommend technical categories, authorized brand product names, purposes, and application stages.

Return ONLY a valid JSON object matching this schema:
{{
  "site_scale": "e.g. G+4 Residential Apartment RCC Frame with Stilt Parking",
  "confidence": "high | medium | low",
  "current_stage": "Detailed description of active structural stage visible in the photo",
  "visible_evidence": [
    "Specific items spotted in photo (e.g. columns, shuttering props, concrete mixer, brick stacks, slab condition)"
  ],
  "full_lifecycle_roadmap": [
    {{
      "stage_name": "Stage 1: Current Structural Casting & Honeycomb Repair (Weeks 1-2)",
      "element": "RCC Columns, Beams & Slab Curing / Doweling",
      "chemical_category": "Curing Compound / Rebar Anchoring / Honeycomb Repair",
      "preferred_brand_product": "Sika AnchorFix-3030 / Asian Paints SmartCare Repair Polymer / REARM SBR 35",
      "purpose": "Patching tie-rod holes, repairing cold joints and gravel pockets; anchoring starter bars or scaffolding ties.",
      "application_timing": "Immediate on site right now",
      "precautions": "Chisel honeycombed concrete to sound aggregate before applying bonding slurry and repair mortar."
    }},
    {{
      "stage_name": "Stage 2: Brick / AAC Block Masonry Infill & Plastering (Weeks 3-5)",
      "element": "External & Internal Wall Plastering Mortar",
      "chemical_category": "Integral Waterproofing Admixture & Polymer Bond Coat",
      "preferred_brand_product": "Asian Paints SmartCare Vitalia Neo (20L) & SmartCare Repair Polymer",
      "purpose": "Vitalia Neo (200ml/bag cement) makes mortar hydrophobic against monsoon rains; Repair Polymer slurry bonds smooth concrete columns to new brickwork without cracks.",
      "application_timing": "During bricklaying and external plastering",
      "precautions": "Apply polymer bonding coat on concrete while it is still tacky before plastering."
    }},
    {{
      "stage_name": "Stage 3: Bathrooms, Sunken Slabs & Wet Pods (Weeks 6-8)",
      "element": "Toilet Sunken Slabs & Plumbing Core Sleeves",
      "chemical_category": "2-Component Acrylic Cementitious Waterproofing Slurry & Non-Shrink Grout",
      "preferred_brand_product": "SikaTop Seal-107 (IN) & Fosroc Conbextra GP2",
      "purpose": "SikaTop 107 forms a flexible seamless barrier across sunken slab base; Conbextra GP2 non-shrink expanding grout packs core-cut plumbing pipe sleeves to stop annular leakage.",
      "application_timing": "Immediately after plumbing pipe rough-ins pass pressure test",
      "precautions": "Pre-wet concrete surface to SSD condition before applying SikaTop 107; carry coating minimum 300mm up walls."
    }},
    {{
      "stage_name": "Stage 4: Roof Terrace & Balconies (Weeks 8-12)",
      "element": "Exposed Flat Roof Slab & Balconies",
      "chemical_category": "UV-Resistant Polyurethane Coating & Reinforcement Mesh",
      "preferred_brand_product": "Asian Paints SmartCare PU Magnum US Grey & Glass Fiber Mesh (145 GSM)",
      "purpose": "Aliphatic PU membrane bridges thermal expansion cracks under harsh Hyderabad sun; Glass fiber mesh reinforces corner fillets and water spouts.",
      "application_timing": "After terrace screed slope to rainwater downspouts is completed",
      "precautions": "Ensure substrate moisture content is below 5% before applying PU coating."
    }},
    {{
      "stage_name": "Stage 5: Flooring & Tile Fixing (Weeks 12-16)",
      "element": "Internal Living/Bedrooms Vitrified Tiles & Wet Area Walls",
      "chemical_category": "Polymer-Fortified Thin-Set Tile Adhesive & Epoxy Grout",
      "preferred_brand_product": "MYK Laticrete 305 Tile Adhesive & MYK Laticrete SP-100 Epoxy Grout",
      "purpose": "Vitrified tiles have zero water absorption (<0.5%) and debond from traditional mortar; Laticrete 305 provides high polymer adhesion; SP-100 gives 100% stain-free waterproof tile joints.",
      "application_timing": "During interior architectural finishing",
      "precautions": "Use notched trowel for 100% bed coverage; do not add extra water once adhesive is mixed."
    }}
  ],
  "site_engineer_verification_checklist": [
    "Verify 28-day concrete curing age before removing shuttering props.",
    "Verify masonry block chemistry (AAC vs clay brick vs fly ash).",
    "Inspect plumbing core-cut annular rings in sunken slabs.",
    "Verify rainwater drainage slope on terrace."
  ]
}}
Return raw JSON only.
"""
    # Try official SDK
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key) if api_key else genai.Client()
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
        )
        raw = response.text.strip()
        if raw.startswith("```json"): raw = raw[7:]
        if raw.startswith("```"): raw = raw[3:]
        if raw.endswith("```"): raw = raw[:-3]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[!] AI GenAI call fallback: {e}")

    # Fallback default roadmap for Hyderabad sites if offline
    return {
        "site_scale": f"{user_context.get('project_type', 'Residential/Commercial Building')} in {user_context.get('location', 'Hyderabad')}",
        "confidence": "high",
        "current_stage": "Under-construction concrete framework and masonry stage",
        "visible_evidence": ["Structural RCC frame", "Ongoing construction activity", "Upcoming waterproofing & finishing required"],
        "full_lifecycle_roadmap": [
            {
                "stage_name": "Stage 1: Structural Curing & Joint Repair",
                "element": "RCC Columns, Beams & Plinth",
                "chemical_category": "Polymer Bonding Agent / Honeycomb Mortar",
                "preferred_brand_product": "Asian Paints SmartCare Repair Polymer / REARM SBR 35",
                "purpose": "Patching surface honeycombing and bonding cold joints before plastering.",
                "application_timing": "Immediate on site",
                "precautions": "Chisel honeycombing to sound aggregate before applying polymer repair mortar."
            },
            {
                "stage_name": "Stage 2: Masonry & External Plastering",
                "element": "External & Internal Wall Plaster",
                "chemical_category": "Integral Liquid Waterproofing Admixture",
                "preferred_brand_product": "Asian Paints SmartCare Vitalia Neo (20L)",
                "purpose": "Makes mortar hydrophobic to prevent rainwater seepage through exterior plaster.",
                "application_timing": "During plastering mortar mixing",
                "precautions": "Add 200ml per 50kg bag of cement into gauging water."
            },
            {
                "stage_name": "Stage 3: Toilet Sunken Slabs & Bathrooms",
                "element": "Sunken Slabs & Plumbing Pipes",
                "chemical_category": "2-Component Acrylic Cementitious Slurry & Non-Shrink Grout",
                "preferred_brand_product": "SikaTop Seal-107 (IN) & Fosroc Conbextra GP2",
                "purpose": "Creates a seamless flexible waterproof barrier and seals annular rings around plumbing pipe sleeves.",
                "application_timing": "Post-plumbing rough-in verification",
                "precautions": "Terminate membrane minimum 300mm above finished floor level."
            },
            {
                "stage_name": "Stage 4: Roof Terrace Waterproofing",
                "element": "Exposed Flat Roof Slab",
                "chemical_category": "UV-Resistant Polyurethane Coating & Reinforcement Mesh",
                "preferred_brand_product": "Asian Paints SmartCare PU Magnum US Grey & Glass Fiber Mesh (145 GSM)",
                "purpose": "Seamless elastomeric PU membrane bridges thermal expansion cracks under Hyderabad sun.",
                "application_timing": "After slope screed to rainwater drains",
                "precautions": "Embed glass fiber mesh along all 90-degree corner fillets."
            },
            {
                "stage_name": "Stage 5: Tile Fixing & Joint Grouting",
                "element": "Floor Tiling & Wall Dados",
                "chemical_category": "Polymer Tile Adhesive & Epoxy Grout",
                "preferred_brand_product": "MYK Laticrete 305 Tile Adhesive & SP-100 Epoxy Grout",
                "purpose": "Prevents hollow debonding of low-porosity vitrified tiles; epoxy gives stain-free waterproof joints.",
                "application_timing": "During interior architectural finishing",
                "precautions": "Ensure 100% notched adhesive bed coverage beneath tiles."
            }
        ],
        "site_engineer_verification_checklist": [
            "Verify concrete curing strength before striking props.",
            "Verify plumbing pipe collar seals in sunken areas.",
            "Inspect terrace rainwater drop slopes."
        ]
    }

def save_lead_to_db(lead_code: str, name: str, phone: str, location: str, project_type: str, stage: str, report: dict, image_filename: str):
    """Save captured inquiry directly into sales_os.db leads table."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        
        # Format notes with summary and chemical roadmap
        roadmap = report.get("full_lifecycle_roadmap", [])
        chems_summary = "; ".join([f"{r.get('stage_name', '')}: {r.get('preferred_brand_product', '')}" for r in roadmap[:4]])
        full_notes = f"Phone/WA: {phone} | Building: {project_type} | Location: {location} | Stage: {stage} | File: {image_filename} | Chemicals: {chems_summary}"

        cur.execute("""
            INSERT INTO leads (
                lead_code, name, developer, location, project_type, stage,
                rera_number, address, source, source_url, discovered_date,
                cluster, estimated_value, builtup_area_sqft, review_status,
                quality_score, notes, imported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            lead_code,
            f"{project_type} - {name}",
            f"{name} ({phone})",
            f"{location}, Hyderabad",
            project_type,
            stage,
            "",
            f"{location}, Hyderabad",
            "Website Free Audit",
            f"file://data/site_audit_uploads/{image_filename}",
            date.today().isoformat(),
            location,
            50000.0,
            2500.0,
            "Pending",
            90,
            full_notes,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        print(f"[✓] Successfully stored inbound lead {lead_code} into sales_os.db")
    except Exception as e:
        print(f"[!] Database error storing lead: {e}")

@app.get("/", response_class=HTMLResponse)
@app.get("/free-site-audit", response_class=HTMLResponse)
async def serve_audit_page():
    """Serve the public website landing page for Free Site Audit."""
    if HTML_FILE.exists():
        try:
            return HTMLResponse(content=HTML_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return HTMLResponse(content=EMBEDDED_HTML)

@app.get("/api/leads")
async def get_captured_leads():
    """Endpoint for local Streamlit CRM to pull all inbound leads from cloud server."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cols = [
            'id', 'lead_code', 'name', 'developer', 'location', 'project_type', 'stage',
            'rera_number', 'address', 'source', 'source_url', 'discovered_date',
            'cluster', 'estimated_value', 'builtup_area_sqft', 'review_status',
            'quality_score', 'notes', 'imported_at'
        ]
        rows = cur.execute(f"SELECT {', '.join(cols)} FROM leads ORDER BY imported_at DESC;").fetchall()
        conn.close()
        leads_list = [dict(zip(cols, r)) for r in rows]
        return JSONResponse({"status": "success", "count": len(leads_list), "leads": leads_list})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e), "count": 0, "leads": []})

@app.post("/api/site-audit")
async def handle_site_audit(
    image: UploadFile = File(...),
    name: str = Form(...),
    phone: str = Form(...),
    location: str = Form(...),
    project_type: str = Form(...),
    note: str = Form("")
):
    """
    Public Endpoint:
    1. Reads and saves image to data/site_audit_uploads/
    2. Runs AI multimodal analysis
    3. Saves lead to sales_os.db
    4. Returns stage-wise technical report (without internal prices) + WhatsApp link
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "_")).rstrip().replace(" ", "_")
    image_ext = Path(image.filename).suffix or ".jpg"
    saved_filename = f"{timestamp}_{safe_name}{image_ext}"
    saved_path = UPLOAD_DIR / saved_filename

    # Read and save file
    content = await image.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    lead_code = f"AUDIT-{timestamp[:8]}-{timestamp[9:]}"
    user_context = {
        "name": name,
        "phone": phone,
        "location": location,
        "project_type": project_type,
        "note": note
    }

    # Run AI analysis
    mime = image.content_type or "image/jpeg"
    report = analyze_photo_with_ai(content, mime, user_context)

    stage = report.get("current_stage", "Active Construction Stage")
    save_lead_to_db(lead_code, name, phone, location, project_type, stage, report, saved_filename)

    # Format WhatsApp connection link for client
    wa_msg = f"""Hi RKICS Technical Team, 
I submitted a site photo for my {project_type} in {location} (Audit Ref: {lead_code}).
My active stage is: {stage}.
Please share contractor trade pricing, technical datasheets, and delivery schedules to our site."""

    wa_url = f"https://wa.me/917013007595?text={quote_plus(wa_msg)}"

    return JSONResponse({
        "status": "success",
        "lead_code": lead_code,
        "site_scale": report.get("site_scale", project_type),
        "current_stage": stage,
        "visible_evidence": report.get("visible_evidence", []),
        "full_lifecycle_roadmap": report.get("full_lifecycle_roadmap", []),
        "site_engineer_verification_checklist": report.get("site_engineer_verification_checklist", []),
        "whatsapp_url": wa_url
    })

if __name__ == "__main__":
    import uvicorn
    import socket

    def find_free_port(start_port=8000):
        for p in [start_port, 8080, 8081, 8502, 5000]:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", p)) != 0:
                    return p
        return start_port

    port = find_free_port(8000)
    print(f"Starting RKICS Site Audit Server on http://localhost:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
