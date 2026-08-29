package com.chillbot.panel;

import android.content.Context;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;

import java.net.Inet6Address;
import java.net.InetAddress;
import java.util.ArrayDeque;
import java.util.Queue;

/**
 * Finds panels announcing themselves on the local network over mdns, so nobody
 * has to know their own ip address.
 *
 * Android will only resolve one service at a time on some versions, so found
 * services go through a queue rather than all being resolved at once.
 */
final class Discovery {

    static final String SERVICE_TYPE = "_chillpanel._tcp.";

    interface Callback {
        /** Called on the main thread with a ready-to-use address. */
        void onFound(String label, String url);
    }

    private final NsdManager nsd;
    private final Callback callback;
    private final Queue<NsdServiceInfo> pending = new ArrayDeque<>();

    private NsdManager.DiscoveryListener discoveryListener;
    private boolean resolving;
    private boolean running;

    Discovery(Context context, Callback callback) {
        this.nsd = (NsdManager) context.getApplicationContext().getSystemService(Context.NSD_SERVICE);
        this.callback = callback;
    }

    void start() {
        if (nsd == null || running) {
            return;
        }
        running = true;
        discoveryListener = new NsdManager.DiscoveryListener() {
            @Override
            public void onDiscoveryStarted(String serviceType) {
            }

            @Override
            public void onServiceFound(NsdServiceInfo info) {
                synchronized (pending) {
                    pending.add(info);
                }
                resolveNext();
            }

            @Override
            public void onServiceLost(NsdServiceInfo info) {
            }

            @Override
            public void onDiscoveryStopped(String serviceType) {
            }

            @Override
            public void onStartDiscoveryFailed(String serviceType, int errorCode) {
                running = false;
            }

            @Override
            public void onStopDiscoveryFailed(String serviceType, int errorCode) {
            }
        };

        try {
            nsd.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, discoveryListener);
        } catch (IllegalArgumentException error) {
            running = false;
        }
    }

    void stop() {
        if (nsd == null || !running || discoveryListener == null) {
            return;
        }
        running = false;
        try {
            nsd.stopServiceDiscovery(discoveryListener);
        } catch (IllegalArgumentException ignored) {
            // Discovery had already stopped on its own.
        }
        discoveryListener = null;
        synchronized (pending) {
            pending.clear();
        }
    }

    private void resolveNext() {
        NsdServiceInfo next;
        synchronized (pending) {
            if (resolving || pending.isEmpty()) {
                return;
            }
            resolving = true;
            next = pending.poll();
        }

        nsd.resolveService(next, new NsdManager.ResolveListener() {
            @Override
            public void onResolveFailed(NsdServiceInfo info, int errorCode) {
                finished();
            }

            @Override
            public void onServiceResolved(NsdServiceInfo info) {
                InetAddress host = info.getHost();
                if (host != null) {
                    String address = host.getHostAddress();
                    if (address != null) {
                        if (host instanceof Inet6Address) {
                            int scope = address.indexOf('%');
                            if (scope > -1) {
                                address = address.substring(0, scope);
                            }
                            address = "[" + address + "]";
                        }
                        callback.onFound(info.getServiceName(),
                                "http://" + address + ":" + info.getPort());
                    }
                }
                finished();
            }

            private void finished() {
                synchronized (pending) {
                    resolving = false;
                }
                resolveNext();
            }
        });
    }
}
