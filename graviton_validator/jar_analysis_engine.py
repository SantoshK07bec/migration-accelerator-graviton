"""
Enhanced JAR analysis module with comprehensive Graviton compatibility assessment.
Integrates knowledge from java_arm_compatibility.py with optimized performance.
"""

import zipfile
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Known libraries with ARM compatibility issues (from java_arm_compatibility.py)
KNOWN_PROBLEMATIC_LIBRARIES = {
    'com.github.jnr:jnr-ffi': {'fixed_in': '2.2.0', 'issue': 'Native FFI compatibility'},
    'net.java.dev.jna:jna': {'fixed_in': '5.5.0', 'issue': 'JNA native libraries'},
    'org.xerial:sqlite-jdbc': {'fixed_in': '3.34.0', 'issue': 'Native SQLite libraries'},
    'io.netty:netty-transport-native-epoll': {'fixed_in': '4.1.46.Final', 'issue': 'Native epoll libraries'},
    'org.rocksdb:rocksdbjni': {'fixed_in': '6.15.2', 'issue': 'RocksDB JNI bindings'},
    'org.lwjgl:lwjgl': {'fixed_in': '3.3.0', 'issue': 'Native game library'},
    'com.github.luben:zstd-jni': {'fixed_in': '1.5.0-4', 'issue': 'Zstandard JNI bindings'},
    'org.lz4:lz4-java': {'fixed_in': '1.8.0', 'issue': 'LZ4 compression JNI'},
    'org.apache.hadoop:hadoop-native': {'fixed_in': '3.3.0', 'issue': 'Hadoop native libraries'},
    'org.apache.arrow:arrow-vector': {'fixed_in': '5.0.0', 'issue': 'Arrow memory management'},
    'org.bytedeco:javacpp': {'fixed_in': '1.5.5', 'issue': 'JavaCPP native integration'}
}

# Libraries known to contain native code (optimized list)
NATIVE_CODE_PATTERNS = [
    'lwjgl', 'jnr', 'jna', 'xerial', 'netty', 'rocksdb', 'bytedeco',
    'hadoop', 'spark', 'tensorflow', 'native', 'jni', 'epoll',
    'zstd', 'lz4', 'arrow', 'crypto', 'ssl', 'blas', 'mkl'
]

# Libraries that may have endianness issues
ENDIANNESS_SENSITIVE_LIBRARIES = [
    'java.nio.ByteBuffer', 'org.apache.hadoop:hadoop-common', 'org.apache.arrow',
    'org.xerial:sqlite-jdbc', 'org.rocksdb:rocksdbjni', 'org.lmdbjava:lmdbjava',
    'org.apache.commons:commons-compress', 'org.apache.lucene:lucene-core'
]

# Libraries that may have memory alignment issues
MEMORY_ALIGNMENT_SENSITIVE_LIBRARIES = [
    'sun.misc.Unsafe', 'jdk.internal.misc.Unsafe', 'org.apache.arrow',
    'org.bytedeco:javacpp', 'org.rocksdb:rocksdbjni', 'org.lmdbjava:lmdbjava',
    'org.apache.hadoop:hadoop-common'
]

# ARM-specific classifiers
ARM_CLASSIFIERS = {
    'io.netty': ['linux-aarch_64', 'linux-arm_64'],
    'org.lwjgl': ['natives-linux-arm64'],
    'org.xerial': ['linux-aarch64'],
    'org.rocksdb': ['linux-aarch64'],
    'com.github.luben': ['linux-aarch64'],
    'org.lz4': ['linux-aarch64']
}

def compare_versions(version1: str, version2: str) -> int:
    """Compare version strings. Returns -1, 0, or 1."""
    def normalize(v):
        v = v.lower().replace('final', '').replace('release', '').strip()
        return [int(x) if x.isdigit() else x for x in re.split(r'[\.\-]', v) if x]
    
    parts1, parts2 = normalize(version1), normalize(version2)
    
    for i in range(max(len(parts1), len(parts2))):
        v1 = parts1[i] if i < len(parts1) else 0
        v2 = parts2[i] if i < len(parts2) else 0
        
        if isinstance(v1, int) and isinstance(v2, int):
            if v1 != v2:
                return -1 if v1 < v2 else 1
        else:
            if str(v1) != str(v2):
                return -1 if str(v1) < str(v2) else 1
    return 0

def check_jar_for_native_code(jar_path: str) -> Dict[str, Any]:
    """Fast native code detection in JAR files."""
    native_info = {
        'has_native_code': False,
        'native_files': [],
        'arm_specific': False,
        'x86_specific': False,
        'platform_dirs': []
    }
    
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # Quick scan of file list (no content reading for performance)
            for entry in jar.namelist():
                entry_lower = entry.lower()
                
                # Check for native library files
                if any(entry_lower.endswith(ext) for ext in ['.so', '.dll', '.dylib', '.jnilib']):
                    native_info['has_native_code'] = True
                    native_info['native_files'].append(entry)
                    
                    # Check architecture indicators
                    if any(arch in entry_lower for arch in ['arm64', 'aarch64', 'arm']):
                        native_info['arm_specific'] = True
                    if any(arch in entry_lower for arch in ['x86_64', 'x86', 'amd64']):
                        native_info['x86_specific'] = True
                
                # Check for platform-specific directories
                platform_indicators = ['linux-arm', 'linux-x86', 'natives-', 'lib/arm', 'lib/x86']
                for indicator in platform_indicators:
                    if indicator in entry_lower:
                        native_info['has_native_code'] = True
                        native_info['platform_dirs'].append(indicator)
                        if 'arm' in indicator:
                            native_info['arm_specific'] = True
                        if any(x in indicator for x in ['x86', 'amd64']):
                            native_info['x86_specific'] = True
                        break
    except Exception:
        pass  # Ignore errors for performance
    
    return native_info

def analyze_jar_metadata(jar_path: str) -> Dict[str, Any]:
    """Extract metadata and perform native code detection."""
    try:
        with zipfile.ZipFile(jar_path, 'r') as jar:
            # Read MANIFEST.MF
            manifest_info = {}
            try:
                manifest_data = jar.read('META-INF/MANIFEST.MF').decode('utf-8')
                for line in manifest_data.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        manifest_info[key.strip()] = value.strip()
            except:
                pass
            
            # Read pom.properties (first one found)
            pom_info = {}
            for file_info in jar.filelist:
                if file_info.filename.endswith('pom.properties'):
                    try:
                        pom_data = jar.read(file_info.filename).decode('utf-8')
                        for line in pom_data.split('\n'):
                            if '=' in line and not line.startswith('#'):
                                key, value = line.split('=', 1)
                                pom_info[key.strip()] = value.strip()
                        break
                    except:
                        pass
            
            # Fast native code detection
            native_info = check_jar_for_native_code(jar_path)
            
            return {
                'jar_path': jar_path,
                'jar_name': Path(jar_path).name,
                'manifest': manifest_info,
                'pom': pom_info,
                'size': Path(jar_path).stat().st_size,
                'file_count': len(jar.filelist),
                'native_info': native_info
            }
    except Exception as e:
        return {
            'jar_path': jar_path,
            'jar_name': Path(jar_path).name,
            'error': str(e),
            'size': Path(jar_path).stat().st_size if Path(jar_path).exists() else 0,
            'native_info': {'has_native_code': False, 'native_files': [], 'arm_specific': False, 'x86_specific': False}
        }

def analyze_compatibility(jar_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced compatibility analysis using comprehensive knowledge base."""
    jar_name = jar_metadata.get('jar_name', '').lower()
    manifest = jar_metadata.get('manifest', {})
    pom = jar_metadata.get('pom', {})
    native_info = jar_metadata.get('native_info', {})
    
    # Extract component information
    group_id = pom.get('groupId', '')
    artifact_id = pom.get('artifactId', '') or manifest.get('Implementation-Title', '') or Path(jar_name).stem
    version = pom.get('version', '') or manifest.get('Implementation-Version', '')
    
    component_key = f"{group_id}:{artifact_id}" if group_id else artifact_id
    
    result = {
        'status': 'COMPATIBLE',
        'confidence': 'HIGH',
        'issues': [],
        'recommendations': [],
        'has_native_code': native_info.get('has_native_code', False),
        'endianness_issues': False,
        'memory_alignment_issues': False,
        'version_info': {'current': version, 'fixed_in': None}
    }
    
    # Check known problematic libraries
    for known_lib, info in KNOWN_PROBLEMATIC_LIBRARIES.items():
        if component_key.startswith(known_lib.split(':')[0]) and artifact_id in known_lib:
            result['has_native_code'] = True
            if version and compare_versions(version, info['fixed_in']) < 0:
                result['status'] = 'INCOMPATIBLE'
                result['confidence'] = 'HIGH'
                result['issues'].append(info['issue'])
                result['recommendations'].append(f"Upgrade to version {info['fixed_in']} or later")
                result['version_info']['fixed_in'] = info['fixed_in']
            else:
                result['issues'].append(f"Previously had {info['issue']}, but fixed in current version")
            break
    
    # Check for native code patterns
    lib_name_lower = artifact_id.lower()
    if any(pattern in lib_name_lower for pattern in NATIVE_CODE_PATTERNS):
        result['has_native_code'] = True
        if result['status'] == 'COMPATIBLE':  # Don't override INCOMPATIBLE status
            result['status'] = 'NEEDS_VERIFICATION'
            result['confidence'] = 'MEDIUM'
            result['issues'].append('Contains native code that may need ARM-specific builds')
            result['recommendations'].append('Test thoroughly on ARM architecture')
    
    # Native code analysis
    if native_info.get('has_native_code'):
        result['has_native_code'] = True
        if native_info.get('arm_specific') and not native_info.get('x86_specific'):
            result['status'] = 'COMPATIBLE'
            result['confidence'] = 'HIGH'
            result['issues'].append('Contains ARM-specific native libraries')
            result['recommendations'].append('No action needed for ARM compatibility')
        elif native_info.get('x86_specific') and not native_info.get('arm_specific'):
            result['status'] = 'INCOMPATIBLE'
            result['confidence'] = 'HIGH'
            result['issues'].append('Contains x86-specific native libraries without ARM equivalents')
            result['recommendations'].append('Look for ARM-compatible version or alternative library')
        elif native_info.get('native_files'):
            if result['status'] == 'COMPATIBLE':
                result['status'] = 'NEEDS_VERIFICATION'
                result['confidence'] = 'MEDIUM'
            result['issues'].append('Native libraries detected - architecture compatibility unknown')
            result['recommendations'].append('Verify native library ARM compatibility')
    
    # Check for endianness issues
    for endianness_lib in ENDIANNESS_SENSITIVE_LIBRARIES:
        if component_key.startswith(endianness_lib) or artifact_id.lower() in endianness_lib.lower():
            result['endianness_issues'] = True
            result['issues'].append('Potential endianness issues on ARM')
            result['recommendations'].append('Test byte order handling on ARM')
            if result['status'] == 'COMPATIBLE':
                result['status'] = 'NEEDS_VERIFICATION'
                result['confidence'] = 'MEDIUM'
            break
    
    # Check for memory alignment issues
    for alignment_lib in MEMORY_ALIGNMENT_SENSITIVE_LIBRARIES:
        if component_key.startswith(alignment_lib) or artifact_id.lower() in alignment_lib.lower():
            result['memory_alignment_issues'] = True
            result['issues'].append('Potential memory alignment issues on ARM')
            result['recommendations'].append('Test memory access patterns on ARM')
            if result['status'] == 'COMPATIBLE':
                result['status'] = 'NEEDS_VERIFICATION'
                result['confidence'] = 'MEDIUM'
            break
    
    # Check for ARM classifiers availability
    for lib_prefix, classifiers in ARM_CLASSIFIERS.items():
        if component_key.startswith(lib_prefix):
            result['recommendations'].append(f"Consider using ARM classifier: {', '.join(classifiers)}")
            break
    
    # Simple heuristics for common compatible libraries
    if result['status'] == 'COMPATIBLE' and not result['has_native_code']:
        compatible_patterns = ['spring', 'hibernate', 'jackson', 'apache', 'google', 'junit', 'aws', 'slf4j', 'logback']
        if any(pattern in lib_name_lower for pattern in compatible_patterns):
            result['confidence'] = 'HIGH'
            result['issues'] = result['issues'] or ['Pure Java library - fully compatible']
    
    return result

def analyze_jar_files_simple(jar_files: List[str]) -> List[Dict[str, Any]]:
    """Analyze multiple JAR files with enhanced compatibility assessment."""
    results = []
    
    for jar_file in jar_files:
        metadata = analyze_jar_metadata(jar_file)
        compatibility = analyze_compatibility(metadata)
        
        result = {
            'file': Path(jar_file).name,
            'path': jar_file,
            'compatibility': compatibility['status'],
            'confidence': compatibility['confidence'],
            'library_name': metadata.get('pom', {}).get('artifactId') or 
                           metadata.get('manifest', {}).get('Implementation-Title') or 
                           Path(jar_file).stem,
            'version': metadata.get('pom', {}).get('version') or 
                      metadata.get('manifest', {}).get('Implementation-Version') or 'unknown',
            'size_mb': round(metadata.get('size', 0) / (1024*1024), 2),
            'file_count': metadata.get('file_count', 0),
            'has_native_code': compatibility['has_native_code'],
            'endianness_issues': compatibility['endianness_issues'],
            'memory_alignment_issues': compatibility['memory_alignment_issues'],
            'issues': compatibility['issues'],
            'recommendations': compatibility['recommendations'],
            'native_files': metadata.get('native_info', {}).get('native_files', []),
            'group_id': metadata.get('pom', {}).get('groupId', ''),
            'version_info': compatibility['version_info']
        }
        
        if 'error' in metadata:
            result['error'] = metadata['error']
            result['compatibility'] = 'ERROR'
            result['confidence'] = 'LOW'
        
        results.append(result)
    
    return results